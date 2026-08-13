"""リポジトリから最新データを読む処理を確かめる。

ここではネットワークへ出ない。取得の部分を差し替えて、
「取れた中身がこうだったら、どう振る舞うか」だけを見る。
実物のGitHubに繋ぐと、GitHubが落ちた日にテストが落ちることになる。

いちばん確かめたいのは、おかしな中身を通さないこと。
通してしまうと、目撃が消えた地図を「最新です」と出すことになる。
"""

import sys
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import remote_data
from remote_data import (
    CSV_NAMES,
    FETCHED_AT_NAME,
    RAW_HOST,
    RemoteDataError,
    load_remote,
    mappable_count,
    raw_url,
)
from ui_styles import EXTERNAL_HOSTS, SERVER_FETCH_HOST, privacy_markdown


HEADER = (
    "No.,年月日,目撃年月日,時間,目撃市町村,場所,天候,目撃時のクマ,"
    "目撃時の目撃者の行動,目撃した環境,その後の対応,人身被害の有無,"
    "推定年齢,目撃頭数,注意事項,緯度,経度"
)

ROW = (
    "1,2026/8/1,2026年8月1日.,14:00,身延町,寺沢地内,晴れ,沢にいた,"
    "近隣住民,集落付近,パトロール実施,無し,コドモ,1,目安です,"
    "35.4703681,138.4374339"
)


def csv_text(rows: int = 1) -> str:
    return "\n".join([HEADER] + [ROW] * rows) + "\n"


def responder(pages: dict[str, str], encoding: str = "utf-8-sig"):
    """URLごとに決めた中身を返す取得役。`load_remote`へ渡す。"""

    def fetch(url: str) -> bytes:
        for name, text in pages.items():
            if url.endswith(name):
                return text.encode(encoding)
        raise AssertionError(f"予定していないURLを読もうとした: {url}")

    return fetch


def healthy(date_text: str = "2026-08-13") -> dict[str, str]:
    pages = {name: csv_text() for name in CSV_NAMES}
    pages[FETCHED_AT_NAME] = f"{date_text}\n"

    return pages


class UrlTest(unittest.TestCase):
    def test_it_points_at_the_published_repository(self):
        url = raw_url("2026kumadata.csv")

        self.assertTrue(url.startswith(f"https://{RAW_HOST}/"))
        self.assertIn(remote_data.REPOSITORY, url)
        self.assertIn(f"/{remote_data.BRANCH}/data/2026kumadata.csv", url)

    def test_it_uses_https(self):
        """平文で取ると、途中で書き換えられても気づけない。"""

        for name in CSV_NAMES + (FETCHED_AT_NAME,):
            with self.subTest(name=name):
                self.assertTrue(raw_url(name).startswith("https://"))


class SuccessTest(unittest.TestCase):
    def test_it_reads_both_files_and_the_date(self):
        records, fetched = load_remote(fetch=responder(healthy()))

        self.assertEqual(2, len(records))
        self.assertEqual(datetime(2026, 8, 13), fetched)

    def test_it_joins_the_files_in_order(self):
        pages = healthy()
        pages[CSV_NAMES[0]] = csv_text(rows=3)
        pages[CSV_NAMES[1]] = csv_text(rows=2)

        records, _ = load_remote(fetch=responder(pages))

        self.assertEqual(5, len(records))

    def test_values_are_stripped_like_the_local_reader(self):
        records, _ = load_remote(fetch=responder(healthy()))

        self.assertEqual("身延町", records[0]["目撃市町村"])

    def test_it_reads_the_date_before_the_files(self):
        """取得日を先に読む。読んでいる間に更新が入っても、
        取得日が実際より新しくなる側へは転ばない。"""

        order = []

        def fetch(url: str) -> bytes:
            order.append(url.rsplit("/", 1)[-1])

            return responder(healthy())(url)

        load_remote(fetch=fetch)

        self.assertEqual(FETCHED_AT_NAME, order[0])


class RejectionTest(unittest.TestCase):
    """おかしな中身は通さない。通すと画面が嘘になる。"""

    def assert_rejected(self, pages, encoding="utf-8-sig"):
        with self.assertRaises(RemoteDataError):
            load_remote(fetch=responder(pages, encoding=encoding))

    def test_an_empty_file_is_rejected(self):
        pages = healthy()
        pages[CSV_NAMES[0]] = "   \n"

        self.assert_rejected(pages)

    def test_a_header_without_sightings_is_rejected(self):
        """県のサイトが空の表を返した日に、目撃0件の地図を出さない。"""

        pages = healthy()
        pages[CSV_NAMES[1]] = HEADER + "\n"

        self.assert_rejected(pages)

    def test_missing_required_columns_are_rejected(self):
        pages = healthy()
        pages[CSV_NAMES[0]] = "No.,年月日\n1,2026/8/1\n"

        self.assert_rejected(pages)

    def test_an_html_error_page_is_rejected(self):
        """落ちているときはHTMLが返る。CSVとして読めない。"""

        pages = healthy()
        pages[CSV_NAMES[0]] = "<html><body>503</body></html>"

        self.assert_rejected(pages)

    def test_text_that_is_not_utf8_is_rejected(self):
        self.assert_rejected(healthy(), encoding="shift_jis")

    def test_data_without_any_mappable_coordinate_is_rejected(self):
        """地図に1件も出せないなら、更新されたと言えない。"""

        broken = ROW.replace("35.4703681,138.4374339", ",")
        pages = {name: "\n".join([HEADER, broken]) + "\n" for name in CSV_NAMES}
        pages[FETCHED_AT_NAME] = "2026-08-13\n"

        self.assert_rejected(pages)

    def test_an_unreadable_date_is_rejected(self):
        pages = healthy()
        pages[FETCHED_AT_NAME] = "きのう\n"

        self.assert_rejected(pages)

    def test_an_empty_date_file_is_rejected(self):
        pages = healthy()
        pages[FETCHED_AT_NAME] = "\n"

        self.assert_rejected(pages)

    def test_a_network_failure_becomes_one_error_type(self):
        """呼ぶ側が1種類だけ捕まえれば、同梱ファイルへ戻せるようにする。"""

        def fetch(url: str) -> bytes:
            raise OSError("接続できません")

        with self.assertRaises(RemoteDataError):
            load_remote(fetch=fetch)


class MappableCountTest(unittest.TestCase):
    def test_coordinates_outside_yamanashi_do_not_count(self):
        """`No.124`のように経度が範囲外の行がある。補正せず数えない。"""

        records = [{"緯度": "35.47", "経度": "38.82"}]

        self.assertEqual(0, mappable_count(records))

    def test_a_trailing_comma_still_counts(self):
        """実データには緯度の末尾にカンマが残る行がある。"""

        records = [{"緯度": "35.4703681,", "経度": "138.4374339"}]

        self.assertEqual(1, mappable_count(records))


class PrivacyTest(unittest.TestCase):
    """画面の説明と、実際に読みに行く先を合わせておく。"""

    def test_the_privacy_text_names_the_server_side_host(self):
        self.assertIn(SERVER_FETCH_HOST, privacy_markdown())

    def test_the_documented_host_is_the_one_actually_used(self):
        self.assertEqual(RAW_HOST, SERVER_FETCH_HOST)

    def test_it_says_the_browser_does_not_connect_there(self):
        """ブラウザがつなぐ相手と混ぜない。混ぜると渡る情報を多く見せる。"""

        text = privacy_markdown()

        self.assertIn("利用者のIPアドレスがGitHubへ渡ることはありません", text)

    def test_the_server_side_host_is_not_in_the_browser_list(self):
        self.assertNotIn(SERVER_FETCH_HOST, {host for host, _ in EXTERNAL_HOSTS})


if __name__ == "__main__":
    unittest.main()
