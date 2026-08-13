"""公開しているリポジトリから、最新のデータを読む。

なぜ必要か:

Streamlit Community Cloudは、GitHubへpushされたことをWebhookで受け取り、
アプリを再起動して新しいコミットを取り直す。この通知が届かないと、
コンテナはデプロイした日のチェックアウトを持ち続ける。
毎日の自動更新がリポジトリには入っているのに、画面だけが古いままになる。

そこで、起動時に置かれたファイルではなく、リポジトリのrawファイルを読む。
再起動を待たずに新しいデータが出せる。

取れなかったときは、同梱のファイルへ戻る（`app.py`側で行う）。
画面が真っ白になるより、少し古いデータが出るほうがよい。

追加のライブラリは使わない。取得は標準ライブラリで行う。
"""

from __future__ import annotations

from datetime import datetime
from http.client import HTTPException
from urllib.request import Request, urlopen

from data_utils import (
    is_inside_yamanashi,
    load_records_from_text,
    parse_coordinate,
    parse_fetched_at,
)


# 読みに行く先。公開先を変えたらここを直す。
REPOSITORY = "shingen-py/sample_20260808"
BRANCH = "main"

# プライバシーの説明にこの名前を書いている。変えたら`ui_styles.py`も直す。
RAW_HOST = "raw.githubusercontent.com"

CSV_NAMES = ("2026kumadata.csv", "2026kumadata_new.csv")
FETCHED_AT_NAME = "fetched_at.txt"

# 画面を触るたびに待たされないよう短くする。
# 取れなければ同梱のファイルへ戻るので、粘る意味がない。
TIMEOUT_SECONDS = 5

# 覚えておく時間。データは1日1回しか変わらないので、1時間で十分新しい。
TTL_SECONDS = 60 * 60

USER_AGENT = "yamanashi-bear-map (app; contact via repository)"


class RemoteDataError(Exception):
    """リポジトリから読めなかった、または読めた中身がおかしかった。

    呼ぶ側がこれ1つを捕まえれば、同梱のファイルへ戻せるようにする。
    """


def raw_url(name: str) -> str:
    """`data/`の中のファイルを指すURLを作る。"""

    return f"https://{RAW_HOST}/{REPOSITORY}/{BRANCH}/data/{name}"


def download(url: str) -> bytes:
    """1つ取ってくる。取れなければ`RemoteDataError`にする。"""

    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            return response.read()
    except (OSError, HTTPException) as error:
        raise RemoteDataError(f"{url} を読めませんでした: {error}") from error


def decode(raw: bytes, name: str) -> str:
    """UTF-8(BOM付き)として読む。読めなければ`RemoteDataError`にする。"""

    if not raw.strip():
        raise RemoteDataError(f"{name}: 中身が空です")

    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise RemoteDataError(f"{name}: UTF-8として読めません") from error


def mappable_count(records: list[dict[str, str]]) -> int:
    """地図に出せる座標を持つ行を数える。"""

    usable = 0
    for record in records:
        latitude = parse_coordinate(record.get("緯度", ""))
        longitude = parse_coordinate(record.get("経度", ""))
        if latitude is not None and longitude is not None:
            if is_inside_yamanashi(latitude, longitude):
                usable += 1

    return usable


def load_remote(fetch=download) -> tuple[list[dict[str, str]], datetime]:
    """リポジトリから目撃データと取得日を読む。

    `scripts/fetch_data.py`と同じ考え方で、全部そろって確認できてから返す。
    途中でおかしなものが1つでもあれば`RemoteDataError`を投げ、
    呼ぶ側が同梱のファイルへ戻れるようにする。
    部分的に新しい、ちぐはぐな状態は作らない。

    取得日を先に読む。読んでいる最中に毎朝の更新が入ると、
    取得日とCSVの新しさがずれる。先に読んでおけば、ずれても
    「取得日のほうが古い」側にしか転ばない。
    実際より新しい日付を出すことにはならない。
    """

    def read(name: str) -> str:
        """1つ読んで文字列にする。失敗は`RemoteDataError`にそろえる。

        `fetch`を差し替えられるようにしてあるので、ここでも受け止める。
        既定の`download`だけに任せると、差し替えたときに別の例外が
        そのまま外へ出てしまい、同梱ファイルへ戻れなくなる。
        """

        try:
            raw = fetch(raw_url(name))
        except RemoteDataError:
            raise
        except (OSError, HTTPException) as error:
            raise RemoteDataError(f"{name} を読めませんでした: {error}") from error

        return decode(raw, name)

    fetched = parse_fetched_at(read(FETCHED_AT_NAME))
    if fetched is None:
        raise RemoteDataError(f"{FETCHED_AT_NAME}: 取得日として読めません")

    records: list[dict[str, str]] = []
    for name in CSV_NAMES:
        text = read(name)

        try:
            rows = load_records_from_text(text)
        except ValueError as error:
            raise RemoteDataError(f"{name}: {error}") from error

        if not rows:
            raise RemoteDataError(f"{name}: 見出しだけで、目撃が1件もありません")

        records.extend(rows)

    if mappable_count(records) == 0:
        raise RemoteDataError("地図に出せる座標が1件もありません")

    return records, fetched
