"""クマ目撃データの読み込みと絞り込み。

画面から独立させ、初心者でも処理を読みやすく、テストしやすい形にしている。
列の意味と扱いの決まりは`DATA.md`に書いてある。
"""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path


REQUIRED_FIELDS = {
    "No.",
    "年月日",
    "目撃市町村",
    "場所",
    "目撃時のクマ",
    "人身被害の有無",
    "注意事項",
    "緯度",
    "経度",
}

# 山梨県のおおよその範囲。これを外れた座標は入力の誤りとみなし、地図に出さない。
LATITUDE_RANGE = (35.0, 36.5)
LONGITUDE_RANGE = (138.0, 139.5)

ALL_MUNICIPALITIES = "すべて"
UNKNOWN_MUNICIPALITY = "市町村不明"
MISSING_VALUE = "記載なし"
UNKNOWN_DATE = "日付不明"

DATE_FORMAT = "%Y/%m/%d"

# 目撃からの経過日数を4段階に分ける境目。指示書§8に合わせる。
# これは「新しさ」の区分であって、危険度ではない。
TONE_THRESHOLDS = ((3, "recent"), (14, "mid"), (30, "older"))
TONE_OLDEST = "oldest"

# 期間の絞り込み。「今季」は基準日が属する年度（4月1日から）とする。
PERIOD_7 = "直近7日"
PERIOD_30 = "直近30日"
PERIOD_SEASON = "今季"
PERIOD_ALL = "すべて"
PERIOD_CHOICES = (PERIOD_7, PERIOD_30, PERIOD_SEASON, PERIOD_ALL)
PERIOD_DAYS = {PERIOD_7: 7, PERIOD_30: 30}

FISCAL_YEAR_START_MONTH = 4


def load_records(csv_path: str | Path) -> list[dict[str, str]]:
    """UTF-8(BOM付き)のCSVを1つ読み、必須列を確認する。

    値は前後の空白だけを取り除き、内容は変えない。
    `No.`の重複はここでは判定しない。`DATA.md`のとおり、
    重複した目撃も消さずに残し、`duplicate_numbers`で検知する。
    """

    path = Path(csv_path)
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fields = set(reader.fieldnames or [])
        missing = REQUIRED_FIELDS - fields
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(f"CSVに必須列がありません: {names}")

        records = [
            {key: (value or "").strip() for key, value in row.items()}
            for row in reader
        ]

    return records


def load_all_records(csv_paths: Iterable[str | Path]) -> list[dict[str, str]]:
    """複数のCSVを読み、渡された順に縦へ結合する。

    年度分と直近1か月分は期間が重ならないため、そのまま並べてよい。
    """

    records: list[dict[str, str]] = []
    for csv_path in csv_paths:
        records.extend(load_records(csv_path))

    return records


def duplicate_numbers(records: list[dict[str, str]]) -> list[str]:
    """結合した結果に`No.`の重複がないかを調べ、重複した番号を返す。"""

    counts = Counter(record["No."] for record in records)

    return sorted(number for number, count in counts.items() if count > 1)


def parse_coordinate(value: str) -> float | None:
    """緯度・経度の文字列を数値にする。できないときはNoneを返す。

    実データには末尾にカンマが残っている行があるため、
    前後の空白とカンマだけを取り除いてから変換する。値そのものは変えない。
    """

    cleaned = (value or "").strip().strip(",").strip()
    if not cleaned:
        return None

    try:
        return float(cleaned)
    except ValueError:
        return None


def is_inside_yamanashi(latitude: float, longitude: float) -> bool:
    """山梨県のおおよその範囲に入っているかを調べる。

    範囲外の座標は入力の誤りとみなす。正しい値は推測できないので直さない。
    """

    return (
        LATITUDE_RANGE[0] <= latitude <= LATITUDE_RANGE[1]
        and LONGITUDE_RANGE[0] <= longitude <= LONGITUDE_RANGE[1]
    )


def split_by_coordinates(
    records: list[dict[str, str]],
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    """地図に出せる行と出せない行に分ける。

    出せる行には、数値にした`緯度数値`と`経度数値`を足して返す。
    元の記録は書き換えない。
    """

    mappable: list[dict[str, object]] = []
    unmappable: list[dict[str, str]] = []

    for record in records:
        latitude = parse_coordinate(record["緯度"])
        longitude = parse_coordinate(record["経度"])
        if latitude is None or longitude is None:
            unmappable.append(record)
            continue
        if not is_inside_yamanashi(latitude, longitude):
            unmappable.append(record)
            continue

        mappable.append({**record, "緯度数値": latitude, "経度数値": longitude})

    return mappable, unmappable


def coordinate_bounds(
    records: list[dict[str, object]],
) -> list[list[float]] | None:
    """地図に出す行が収まる四角を返す。`[[南西の緯度, 経度], [北東の緯度, 経度]]`。

    `split_by_coordinates`が返した行（`緯度数値`と`経度数値`を持つ行）に使う。
    1件しかないときは南西と北東が同じ点になる。寄りすぎないよう、
    使う側で拡大率の上限を決める。
    """

    if not records:
        return None

    latitudes = [float(record["緯度数値"]) for record in records]
    longitudes = [float(record["経度数値"]) for record in records]

    return [
        [min(latitudes), min(longitudes)],
        [max(latitudes), max(longitudes)],
    ]


def base_municipality(name: str) -> str:
    """末尾の「市・町・村」を外した名前を返す。表記ゆれを揃えるために使う。"""

    stripped = (name or "").strip()
    if stripped.endswith(("市", "町", "村")):
        return stripped[:-1]

    return stripped


def available_municipalities(records: list[dict[str, str]]) -> list[str]:
    """画面のプルダウンに出す市町村名を、重複なく並べて返す。

    末尾の「市・町・村」の有無だけをゆれとみなし、付いている表記へ寄せる。
    空欄はプルダウンに出さない。
    """

    representatives: dict[str, str] = {}
    for record in records:
        name = record["目撃市町村"].strip()
        if not name:
            continue

        base = base_municipality(name)
        current = representatives.get(base)
        if current is None or len(name) > len(current):
            representatives[base] = name

    return sorted(representatives.values())


def municipality_counts(records: list[dict[str, str]]) -> dict[str, int]:
    """市町村ごとの目撃件数を返す。表記ゆれは同じ市町村として数える。

    ここで数えるのは目撃の総数で、座標がなく地図に出せないものも含む。
    プルダウンの併記に使う。
    """

    counted: Counter[str] = Counter()
    for record in records:
        name = record["目撃市町村"].strip()
        if not name:
            continue
        counted[base_municipality(name)] += 1

    return {
        name: counted[base_municipality(name)]
        for name in available_municipalities(records)
    }


def filter_by_municipality(
    records: list[dict[str, str]],
    municipality: str = ALL_MUNICIPALITIES,
) -> list[dict[str, str]]:
    """選ばれた市町村で絞り込む。表記ゆれは同じ市町村として扱う。"""

    if municipality == ALL_MUNICIPALITIES:
        return list(records)

    target = base_municipality(municipality)

    return [
        record
        for record in records
        if base_municipality(record["目撃市町村"]) == target
    ]


def municipality_label(record: dict[str, str]) -> str:
    """画面に出す市町村名。空欄のときは「市町村不明」と出す。"""

    return record["目撃市町村"].strip() or UNKNOWN_MUNICIPALITY


def record_date(record: dict[str, str]) -> datetime | None:
    """目撃日を日付として返す。`YYYY/M/D`として読めないときはNoneを返す。"""

    try:
        return datetime.strptime(record["年月日"].strip(), DATE_FORMAT)
    except ValueError:
        return None


def date_label(record: dict[str, str]) -> str:
    """画面に出す日付。読めないときは「日付不明」と出す。"""

    if record_date(record) is None:
        return UNKNOWN_DATE

    return record["年月日"].strip()


def reference_date(records: list[dict[str, str]]) -> datetime | None:
    """経過日数を数える基準日。データの中でいちばん新しい目撃日。

    今日を基準にすると、データを更新しないまま日が経つだけで
    すべての目撃が「古い」側へ寄ってしまう。データの中で閉じた基準にする。
    """

    dates = [date for date in map(record_date, records) if date is not None]

    return max(dates) if dates else None


def days_ago(record: dict[str, str], reference: datetime | None) -> int | None:
    """基準日から何日前の目撃かを返す。日付が読めなければNoneを返す。"""

    date = record_date(record)
    if date is None or reference is None:
        return None

    return (reference - date).days


def sighting_tone(days: int | None) -> str:
    """経過日数を4段階の区分名にする。日付が読めない場合はいちばん古い扱い。"""

    if days is None:
        return TONE_OLDEST

    for limit, name in TONE_THRESHOLDS:
        if days <= limit:
            return name

    return TONE_OLDEST


def _number_key(record: dict[str, str]) -> int:
    """`No.`を数として返す。数として読めない行は最後へ回すため-1にする。"""

    value = str(record.get("No.", "")).strip()

    return int(value) if value.isdigit() else -1


def sort_by_date_desc(records: list[dict[str, str]]) -> list[dict[str, str]]:
    """日付の新しい順に並べ替えた新しいリストを返す。元のリストは並べ替えない。

    同じ日付のときは`No.`の大きい順にする。順番を決めておかないと、
    画面を開くたびに並びが変わって「さっき見た行」を見失う。
    日付が読めない行は、置く場所を決められないので末尾へまとめる。
    """

    dated: list[tuple[datetime, int, dict[str, str]]] = []
    undated: list[tuple[int, dict[str, str]]] = []

    for record in records:
        date = record_date(record)
        if date is None:
            undated.append((_number_key(record), record))
        else:
            dated.append((date, _number_key(record), record))

    dated.sort(key=lambda row: (row[0], row[1]), reverse=True)
    undated.sort(key=lambda row: row[0], reverse=True)

    return [row[-1] for row in dated] + [row[-1] for row in undated]


def tone_ranges() -> list[tuple[str, str]]:
    """4段階の区分名と、その説明文を返す。

    しきい値から組み立てるので、`TONE_THRESHOLDS`を変えれば凡例も一緒に変わる。
    """

    ranges = []
    lower = 0
    for limit, name in TONE_THRESHOLDS:
        ranges.append((name, f"{lower}〜{limit}日前"))
        lower = limit + 1

    ranges.append((TONE_OLDEST, f"{lower}日前より古い"))

    return ranges


def days_ago_label(days: int | None) -> str:
    """ツールチップに出す言葉。色だけに意味を持たせないために使う。"""

    if days is None:
        return UNKNOWN_DATE
    if days == 0:
        return "当日"

    return f"{days}日前"


def season_start(reference: datetime) -> datetime:
    """基準日が属する年度の初日（4月1日）を返す。"""

    year = reference.year
    if reference.month < FISCAL_YEAR_START_MONTH:
        year -= 1

    return datetime(year, FISCAL_YEAR_START_MONTH, 1)


def filter_by_period(
    records: list[dict[str, str]],
    period: str = PERIOD_ALL,
    reference: datetime | None = None,
) -> list[dict[str, str]]:
    """期間で絞り込む。

    「直近N日」は、基準日を1日目として数えたN日分（経過日数が0からN-1）。
    日付が読めない目撃は、期間を指定したときは外す。置く場所が決められないため。
    「すべて」のときだけ残す。
    """

    if period == PERIOD_ALL or reference is None:
        return list(records)

    if period == PERIOD_SEASON:
        start = season_start(reference)
        return [
            record
            for record in records
            if (date := record_date(record)) is not None and date >= start
        ]

    limit = PERIOD_DAYS[period]

    return [
        record
        for record in records
        if (days := days_ago(record, reference)) is not None and 0 <= days < limit
    ]


def data_period(records: list[dict[str, str]]) -> tuple[str, str] | None:
    """収録期間の最初と最後の日を返す。読める日付が1つもなければNoneを返す。

    0件のときの案内に使う。データを入れ替えても自動で追従する。
    """

    dates = [date for date in map(record_date, records) if date is not None]

    if not dates:
        return None

    first, last = min(dates), max(dates)

    return (
        f"{first.year}年{first.month}月{first.day}日",
        f"{last.year}年{last.month}月{last.day}日",
    )


def sighting_details(record: dict[str, str]) -> list[tuple[str, str]]:
    """ピンの吹き出しに出す項目を、見出しと値の組で返す。

    値が空欄の項目は「記載なし」にする。空欄でもピンは消さない。
    """

    return [
        ("日付", date_label(record)),
        ("時間", record.get("時間", "").strip() or MISSING_VALUE),
        ("場所", record["場所"].strip() or MISSING_VALUE),
        ("状況", record["目撃時のクマ"].strip() or MISSING_VALUE),
        ("人身被害", record["人身被害の有無"].strip() or MISSING_VALUE),
    ]
