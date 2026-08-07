"""山梨県のクマ目撃CSVを取得して差し替える。

使い方:
    python scripts/fetch_data.py

差し替える前に、取れたデータが読めるかを確かめる。
県のサイトが一時的に落ちてエラーページが返ってきたときなどに、
空や壊れた中身で上書きしてしまうと、画面から目撃が消えてしまう。

終了コード:
    0  取得できた（中身が変わっていない場合も含む）
    1  取得できなかった、または取れたデータがおかしかった

追加のライブラリは使わない。取得は標準ライブラリで行う。
"""

from __future__ import annotations

import csv
import io
import sys
from datetime import date
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data_utils import (  # noqa: E402
    REQUIRED_FIELDS,
    is_inside_yamanashi,
    parse_coordinate,
)


DATA_DIR = ROOT / "data"
FETCHED_AT_PATH = DATA_DIR / "fetched_at.txt"

# 取得元。年度が変わるとファイル名とURLが変わる可能性がある。
# その場合はここを直す。
SOURCES = (
    (
        "2026kumadata.csv",
        "https://catalog.dataplatform-yamanashi.jp/dataset/"
        "bed5301d-75b2-4976-8687-2b2721ae143a/resource/"
        "89d2478e-e29e-46e3-9ad3-19bf44822d4d/download/2026kumadata.csv",
    ),
    (
        "2026kumadata_new.csv",
        "https://catalog.dataplatform-yamanashi.jp/dataset/"
        "0e9f8d75-5773-4cac-be4d-68d50bd819d8/resource/"
        "62796404-c80f-47d6-ae88-222f844ee958/download/2026kumadata_new.csv",
    ),
)

TIMEOUT_SECONDS = 30
USER_AGENT = "yamanashi-bear-map (data refresh; contact via repository)"


def download(url: str) -> bytes:
    """CSVを取ってくる。取れなければ例外を投げる。"""

    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
        return response.read()


def problems_in(raw: bytes) -> list[str]:
    """取れたデータの問題点を並べて返す。空なら差し替えてよい。

    ここを通らなかったものは、今あるファイルを残したまま終わる。
    """

    problems = []

    if not raw.strip():
        return ["中身が空です"]

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return ["UTF-8として読めません"]

    rows = list(csv.DictReader(io.StringIO(text, newline="")))
    if not rows:
        return ["見出しだけで、目撃が1件もありません"]

    missing = REQUIRED_FIELDS - set(rows[0])
    if missing:
        problems.append(f"必須列がありません: {', '.join(sorted(missing))}")

    if "緯度" in rows[0] and "経度" in rows[0]:
        usable = 0
        for row in rows:
            latitude = parse_coordinate(row["緯度"])
            longitude = parse_coordinate(row["経度"])
            if latitude is not None and longitude is not None:
                if is_inside_yamanashi(latitude, longitude):
                    usable += 1
        if usable == 0:
            problems.append("地図に出せる座標が1件もありません")

    return problems


def replace_file(path: Path, raw: bytes) -> bool:
    """中身が変わっていれば差し替える。変わったかどうかを返す。

    途中で止まっても壊れたファイルが残らないよう、
    別名で書いてから置き換える。
    """

    if path.exists() and path.read_bytes() == raw:
        return False

    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(raw)
    temporary.replace(path)

    return True


def record_fetched_at(today: date) -> None:
    """取得できた日を書き残す。画面の出所表示に使う。"""

    FETCHED_AT_PATH.write_text(f"{today:%Y-%m-%d}\n", encoding="utf-8")


def main() -> int:
    fetched = []

    for name, url in SOURCES:
        print(f"取得中: {name}")
        try:
            raw = download(url)
        except (URLError, OSError) as error:
            print(f"  取得できませんでした: {error}")
            print("今あるファイルは残します。")
            return 1

        problems = problems_in(raw)
        if problems:
            print(f"  取れたデータがおかしいので使いません: {'、'.join(problems)}")
            print("今あるファイルは残します。")
            return 1

        fetched.append((DATA_DIR / name, raw))
        print(f"  確認できました（{len(raw):,} バイト）")

    # 2つとも確認できてから差し替える。片方だけ新しい状態にしない。
    changed = [path.name for path, raw in fetched if replace_file(path, raw)]
    record_fetched_at(date.today())

    if changed:
        print(f"差し替えました: {', '.join(changed)}")
    else:
        print("中身は変わっていませんでした。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
