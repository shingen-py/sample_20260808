"""データ取得スクリプトを確かめる。

ネットワークには触らない。取得そのものではなく、
「取れたデータを差し替えてよいか」の判断を確かめる。
ここが甘いと、県のサイトが落ちた日に空のファイルで上書きしてしまう。
"""

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_data import (  # noqa: E402
    SOURCES,
    problems_in,
    record_fetched_at,
    replace_file,
)


def real_csv() -> bytes:
    return (ROOT / "data" / "2026kumadata.csv").read_bytes()


class ProblemsInTest(unittest.TestCase):
    def test_the_real_file_passes(self):
        self.assertEqual([], problems_in(real_csv()))

    def test_an_empty_response_is_rejected(self):
        """県のサイトが落ちていると空が返ることがある。"""

        for raw in (b"", b"   ", b"\n\n"):
            with self.subTest(raw=raw):
                self.assertEqual(["中身が空です"], problems_in(raw))

    def test_an_error_page_is_rejected(self):
        """HTMLのエラーページが返ってきても、CSVとして受け取らない。"""

        raw = "<!DOCTYPE html><html><body>502 Bad Gateway</body></html>".encode()

        self.assertNotEqual([], problems_in(raw))

    def test_a_file_in_another_encoding_is_rejected(self):
        raw = "No.,年月日,目撃市町村\n1,2026/4/2,甲府市\n".encode("cp932")

        self.assertEqual(["UTF-8として読めません"], problems_in(raw))

    def test_a_header_without_rows_is_rejected(self):
        header = real_csv().decode("utf-8-sig").splitlines()[0]

        self.assertEqual(
            ["見出しだけで、目撃が1件もありません"],
            problems_in(header.encode("utf-8")),
        )

    def test_a_missing_column_is_reported(self):
        text = real_csv().decode("utf-8-sig")
        without_place = "\n".join(
            ",".join(part for index, part in enumerate(line.split(",")) if index != 5)
            for line in text.splitlines()
        )

        problems = problems_in(without_place.encode("utf-8"))

        self.assertTrue(any("必須列がありません" in p for p in problems))

    def test_a_file_with_no_usable_coordinates_is_rejected(self):
        """列はそろっているが座標が全部壊れている、という壊れ方もある。"""

        lines = real_csv().decode("utf-8-sig").splitlines()
        header = lines[0]
        broken = [header]
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) >= 2:
                parts[-1] = "?"
                parts[-2] = "?"
            broken.append(",".join(parts))

        problems = problems_in("\n".join(broken).encode("utf-8"))

        self.assertIn("地図に出せる座標が1件もありません", problems)


class ReplaceFileTest(unittest.TestCase):
    def test_the_same_content_is_not_rewritten(self):
        """毎日同じ中身で書き直すと、変わっていないのに変更として扱われる。"""

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "data.csv"
            path.write_bytes(b"abc")

            self.assertFalse(replace_file(path, b"abc"))

    def test_new_content_is_written(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "data.csv"
            path.write_bytes(b"abc")

            self.assertTrue(replace_file(path, b"xyz"))
            self.assertEqual(b"xyz", path.read_bytes())

    def test_a_missing_file_is_created(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "data.csv"

            self.assertTrue(replace_file(path, b"abc"))
            self.assertEqual(b"abc", path.read_bytes())

    def test_no_temporary_file_is_left_behind(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "data.csv"
            replace_file(path, b"abc")

            self.assertEqual(["data.csv"], [p.name for p in Path(temp_dir).iterdir()])

    def test_line_endings_are_kept_as_they_arrive(self):
        """CRLFをLFに直したりしない。中身をそのまま保つ。"""

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "data.csv"
            replace_file(path, b"a,b\r\n1,2\r\n")

            self.assertEqual(b"a,b\r\n1,2\r\n", path.read_bytes())


class RecordFetchedAtTest(unittest.TestCase):
    def test_the_date_can_be_read_back(self):
        from data_utils import fetched_at

        import fetch_data

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "fetched_at.txt"
            original = fetch_data.FETCHED_AT_PATH
            fetch_data.FETCHED_AT_PATH = path
            try:
                record_fetched_at(date(2026, 12, 25))
            finally:
                fetch_data.FETCHED_AT_PATH = original

            self.assertEqual("2026-12-25\n", path.read_text(encoding="utf-8"))
            self.assertEqual(2026, fetched_at(path).year)
            self.assertEqual(12, fetched_at(path).month)


class SourcesTest(unittest.TestCase):
    def test_it_fetches_both_files(self):
        self.assertEqual(2, len(SOURCES))

    def test_the_names_match_the_files_the_app_reads(self):
        names = {name for name, _ in SOURCES}

        self.assertEqual({"2026kumadata.csv", "2026kumadata_new.csv"}, names)
        for name in names:
            self.assertTrue((ROOT / "data" / name).is_file())

    def test_no_extra_library_is_needed(self):
        """取得は標準ライブラリで行う。requirements.txtを増やさない。"""

        source = (ROOT / "scripts" / "fetch_data.py").read_text(encoding="utf-8")

        self.assertIn("from urllib.request import", source)
        self.assertNotIn("import requests", source)
        self.assertNotIn("import httpx", source)


if __name__ == "__main__":
    unittest.main()
