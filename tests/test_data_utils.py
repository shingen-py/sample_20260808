import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from data_utils import (
    PERIOD_30,
    PERIOD_7,
    PERIOD_ALL,
    PERIOD_CHOICES,
    PERIOD_SEASON,
    available_municipalities,
    coordinate_bounds,
    data_period,
    date_label,
    days_ago,
    days_ago_label,
    duplicate_numbers,
    filter_by_municipality,
    filter_by_period,
    is_inside_yamanashi,
    load_all_records,
    load_records,
    municipality_counts,
    municipality_label,
    parse_coordinate,
    record_date,
    reference_date,
    season_start,
    sighting_details,
    sighting_tone,
    sort_by_date_desc,
    split_by_coordinates,
    tone_ranges,
)


ROOT = Path(__file__).resolve().parent.parent
TEST_DATA = Path(__file__).resolve().parent / "data"
PART1 = TEST_DATA / "kuma_part1.csv"
PART2 = TEST_DATA / "kuma_part2.csv"
REAL_FILES = [
    ROOT / "data" / "2026kumadata.csv",
    ROOT / "data" / "2026kumadata_new.csv",
]


class LoadRecordsTest(unittest.TestCase):
    def test_two_files_are_combined_in_order(self):
        records = load_all_records([PART1, PART2])

        self.assertEqual(8, len(records))
        self.assertEqual(
            ["1", "2", "3", "4", "5", "6", "7", "8"],
            [record["No."] for record in records],
        )

    def test_all_columns_are_kept(self):
        records = load_records(PART1)

        self.assertEqual(17, len(records[0]))
        self.assertEqual("甲府市", records[0]["目撃市町村"])
        self.assertEqual("右左口町", records[0]["場所"])

    def test_values_are_not_changed_beyond_stripping_spaces(self):
        """緯度の末尾のカンマはここでは取り除かない。地図に出す直前で扱う。"""

        records = load_records(PART1)

        self.assertEqual("35.4703681,", records[1]["緯度"])
        self.assertEqual("", records[2]["緯度"])
        self.assertEqual("", records[3]["目撃市町村"])

    def test_real_data_can_be_loaded(self):
        records = load_all_records(REAL_FILES)

        self.assertEqual(160, len(records))

    def test_missing_required_column_is_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "broken.csv"
            csv_path.write_text("No.,年月日\n1,2026/4/2\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "必須列"):
                load_records(csv_path)


class DuplicateNumbersTest(unittest.TestCase):
    def test_real_data_has_no_duplicate_numbers(self):
        records = load_all_records(REAL_FILES)

        self.assertEqual([], duplicate_numbers(records))

    def test_duplicate_number_is_detected(self):
        records = [{"No.": "1"}, {"No.": "2"}, {"No.": "1"}]

        self.assertEqual(["1"], duplicate_numbers(records))

    def test_duplicated_record_is_not_removed_on_load(self):
        """DATA.mdのとおり、`No.`が重複しても消さずに両方残す。"""

        records = load_all_records([PART1, PART1])

        self.assertEqual(10, len(records))
        self.assertEqual(
            ["1", "2", "3", "4", "5"], duplicate_numbers(records)
        )


class CoordinateTest(unittest.TestCase):
    def test_trailing_comma_and_space_are_removed(self):
        self.assertEqual(35.4703681, parse_coordinate("35.4703681,"))
        self.assertEqual(35.49557612608502, parse_coordinate("35.49557612608502, "))

    def test_blank_or_broken_value_becomes_none(self):
        self.assertIsNone(parse_coordinate(""))
        self.assertIsNone(parse_coordinate("   "))
        self.assertIsNone(parse_coordinate("不明"))

    def test_out_of_range_coordinate_is_rejected(self):
        self.assertTrue(is_inside_yamanashi(35.53508764, 138.8243704))
        self.assertFalse(is_inside_yamanashi(35.53508764, 38.8243704))

    def test_records_are_split_into_mappable_and_unmappable(self):
        records = load_all_records([PART1, PART2])

        mappable, unmappable = split_by_coordinates(records)

        self.assertEqual(6, len(mappable))
        self.assertEqual(["3", "6"], [record["No."] for record in unmappable])

    def test_mappable_record_gets_numeric_coordinates(self):
        records = load_records(PART1)

        mappable, _ = split_by_coordinates(records)
        comma_row = [r for r in mappable if r["No."] == "2"][0]

        self.assertEqual(35.4703681, comma_row["緯度数値"])
        self.assertEqual(138.4374339, comma_row["経度数値"])

    def test_original_record_is_not_changed(self):
        records = load_records(PART1)

        split_by_coordinates(records)

        self.assertEqual("35.4703681,", records[1]["緯度"])
        self.assertNotIn("緯度数値", records[1])

    def test_real_data_split(self):
        records = load_all_records(REAL_FILES)

        mappable, unmappable = split_by_coordinates(records)

        self.assertEqual(156, len(mappable))
        self.assertEqual(
            ["14", "15", "97", "124"], [record["No."] for record in unmappable]
        )


class CoordinateBoundsTest(unittest.TestCase):
    def test_bounds_cover_every_point(self):
        records = load_all_records([PART1, PART2])
        mappable, _ = split_by_coordinates(records)

        (south, west), (north, east) = coordinate_bounds(mappable)

        for record in mappable:
            with self.subTest(number=record["No."]):
                self.assertLessEqual(south, record["緯度数値"])
                self.assertGreaterEqual(north, record["緯度数値"])
                self.assertLessEqual(west, record["経度数値"])
                self.assertGreaterEqual(east, record["経度数値"])

    def test_single_point_gives_a_bounds_with_no_area(self):
        """1件のときは点になる。使う側で拡大率の上限を決める必要がある。"""

        one = [{"緯度数値": 35.5, "経度数値": 138.6}]

        self.assertEqual([[35.5, 138.6], [35.5, 138.6]], coordinate_bounds(one))

    def test_no_records_gives_nothing(self):
        self.assertIsNone(coordinate_bounds([]))

    def test_real_municipality_bounds_stay_inside_yamanashi(self):
        records = load_all_records(REAL_FILES)
        mappable, _ = split_by_coordinates(records)
        minobu = filter_by_municipality(mappable, "身延町")

        (south, west), (north, east) = coordinate_bounds(minobu)

        self.assertTrue(35.0 <= south <= north <= 36.5)
        self.assertTrue(138.0 <= west <= east <= 139.5)


class MunicipalityTest(unittest.TestCase):
    def test_blank_municipality_is_not_offered_in_the_list(self):
        records = load_all_records([PART1, PART2])

        names = available_municipalities(records)

        self.assertNotIn("", names)
        self.assertEqual(6, len(names))

    def test_name_variants_are_merged_into_the_longer_form(self):
        records = load_all_records([PART1, PART2])

        names = available_municipalities(records)

        self.assertIn("富士河口湖町", names)
        self.assertNotIn("富士河口湖", names)

    def test_filter_treats_variants_as_the_same_municipality(self):
        records = load_all_records([PART1, PART2])

        results = filter_by_municipality(records, "富士河口湖町")

        self.assertEqual(["7", "8"], [record["No."] for record in results])

    def test_filter_all_keeps_every_record(self):
        records = load_all_records([PART1, PART2])

        self.assertEqual(8, len(filter_by_municipality(records, "すべて")))

    def test_blank_municipality_is_labelled_as_unknown(self):
        records = load_records(PART1)

        self.assertEqual("市町村不明", municipality_label(records[3]))
        self.assertEqual("甲府市", municipality_label(records[0]))

    def test_real_data_municipality_list(self):
        records = load_all_records(REAL_FILES)

        names = available_municipalities(records)

        self.assertEqual(25, len(names))
        self.assertNotIn("富士河口湖", names)
        self.assertEqual(9, len(filter_by_municipality(records, "富士河口湖町")))


class SightingDetailsTest(unittest.TestCase):
    def test_five_items_are_returned_in_order(self):
        records = load_records(PART1)

        labels = [label for label, _ in sighting_details(records[0])]

        self.assertEqual(["日付", "時間", "場所", "状況", "人身被害"], labels)

    def test_values_come_from_the_record(self):
        records = load_records(PART1)

        details = dict(sighting_details(records[0]))

        self.assertEqual("2026/4/2", details["日付"])
        self.assertEqual("14:00", details["時間"])
        self.assertEqual("右左口町", details["場所"])
        self.assertEqual("沢にいた。避難したためその後は不明", details["状況"])
        self.assertEqual("無し", details["人身被害"])

    def test_blank_values_are_shown_as_missing(self):
        """状況と時間が空欄の行でも、ピンは消さずに「記載なし」と出す。"""

        records = load_records(PART1)

        details = dict(sighting_details(records[4]))

        self.assertEqual("記載なし", details["状況"])
        self.assertEqual("記載なし", details["時間"])
        self.assertEqual("無", details["人身被害"])

    def test_unreadable_date_is_shown_as_unknown(self):
        self.assertEqual("2026/4/2", date_label({"年月日": "2026/4/2"}))
        self.assertEqual("2026/12/31", date_label({"年月日": "2026/12/31"}))
        self.assertEqual("日付不明", date_label({"年月日": ""}))
        self.assertEqual("日付不明", date_label({"年月日": "令和8年4月2日"}))

    def test_every_real_record_produces_five_items(self):
        records = load_all_records(REAL_FILES)

        for record in records:
            details = sighting_details(record)
            self.assertEqual(5, len(details))
            for _, value in details:
                self.assertNotEqual("", value)

    def test_real_data_has_no_unreadable_date(self):
        records = load_all_records(REAL_FILES)

        unreadable = [r["No."] for r in records if date_label(r) == "日付不明"]

        self.assertEqual([], unreadable)


class MunicipalityCountsTest(unittest.TestCase):
    def test_counts_match_the_dropdown_list(self):
        """プルダウンに出す市町村と、件数の見出しが1対1で対応する。"""

        records = load_all_records(REAL_FILES)

        counts = municipality_counts(records)

        self.assertEqual(available_municipalities(records), sorted(counts))

    def test_name_variants_are_counted_together(self):
        records = load_all_records(REAL_FILES)

        counts = municipality_counts(records)

        self.assertEqual(9, counts["富士河口湖町"])
        self.assertNotIn("富士河口湖", counts)

    def test_counts_include_records_that_cannot_be_mapped(self):
        """西桂町の1件は座標が範囲外だが、目撃の総数としては数える。"""

        records = load_all_records(REAL_FILES)

        self.assertEqual(1, municipality_counts(records)["西桂町"])

    def test_blank_municipality_is_not_counted(self):
        records = load_all_records([PART1, PART2])

        counts = municipality_counts(records)

        self.assertNotIn("", counts)
        self.assertEqual(7, sum(counts.values()))

    def test_total_matches_records_with_a_municipality(self):
        records = load_all_records(REAL_FILES)

        named = [r for r in records if r["目撃市町村"].strip()]

        self.assertEqual(len(named), sum(municipality_counts(records).values()))


class DataPeriodTest(unittest.TestCase):
    def test_real_data_period(self):
        records = load_all_records(REAL_FILES)

        self.assertEqual(("2026年4月2日", "2026年8月5日"), data_period(records))

    def test_period_ignores_unreadable_dates(self):
        records = [
            {"年月日": "令和8年4月2日"},
            {"年月日": "2026/5/1"},
            {"年月日": ""},
            {"年月日": "2026/5/20"},
        ]

        self.assertEqual(("2026年5月1日", "2026年5月20日"), data_period(records))

    def test_period_is_none_when_no_date_is_readable(self):
        self.assertIsNone(data_period([{"年月日": ""}, {"年月日": "不明"}]))


def make_record(date_text: str) -> dict[str, str]:
    return {"年月日": date_text}


class ReferenceDateTest(unittest.TestCase):
    def test_reference_is_the_newest_date_in_the_data(self):
        """今日ではなくデータ内の最新日を基準にする。日が経っても色分けが崩れない。"""

        records = load_all_records(REAL_FILES)

        self.assertEqual(datetime(2026, 8, 5), reference_date(records))

    def test_reference_ignores_unreadable_dates(self):
        records = [make_record("令和8年4月2日"), make_record("2026/5/1")]

        self.assertEqual(datetime(2026, 5, 1), reference_date(records))

    def test_reference_is_none_without_any_readable_date(self):
        self.assertIsNone(reference_date([make_record("")]))


class DaysAgoTest(unittest.TestCase):
    def setUp(self):
        self.reference = datetime(2026, 8, 5)

    def test_days_are_counted_from_the_reference(self):
        self.assertEqual(0, days_ago(make_record("2026/8/5"), self.reference))
        self.assertEqual(1, days_ago(make_record("2026/8/4"), self.reference))
        self.assertEqual(35, days_ago(make_record("2026/7/1"), self.reference))

    def test_unreadable_date_has_no_days(self):
        self.assertIsNone(days_ago(make_record("不明"), self.reference))
        self.assertIsNone(days_ago(make_record("2026/8/5"), None))

    def test_label_is_readable_without_colour(self):
        """色だけに意味を持たせない（指示書§18）。言葉でも分かるようにする。"""

        self.assertEqual("当日", days_ago_label(0))
        self.assertEqual("2日前", days_ago_label(2))
        self.assertEqual("日付不明", days_ago_label(None))


class SightingToneTest(unittest.TestCase):
    def test_four_steps_follow_the_spec(self):
        """0〜3日、4〜14日、15〜30日、31日以上（指示書§8）。"""

        self.assertEqual("recent", sighting_tone(0))
        self.assertEqual("recent", sighting_tone(3))
        self.assertEqual("mid", sighting_tone(4))
        self.assertEqual("mid", sighting_tone(14))
        self.assertEqual("older", sighting_tone(15))
        self.assertEqual("older", sighting_tone(30))
        self.assertEqual("oldest", sighting_tone(31))

    def test_unknown_date_is_treated_as_the_oldest(self):
        self.assertEqual("oldest", sighting_tone(None))

    def test_tone_names_match_the_palette(self):
        """凡例とマーカーの色がずれないよう、名前をui_styles側と合わせる。"""

        from ui_styles import TONE_COLORS

        tones = {sighting_tone(days) for days in (0, 5, 20, 100, None)}

        self.assertEqual(set(TONE_COLORS), tones)

    def test_ranges_describe_every_tone_in_words(self):
        """凡例の文言。色だけに意味を持たせないための土台。"""

        self.assertEqual(
            [
                ("recent", "0〜3日前"),
                ("mid", "4〜14日前"),
                ("older", "15〜30日前"),
                ("oldest", "31日前より古い"),
            ],
            tone_ranges(),
        )

    def test_ranges_have_no_gap_or_overlap(self):
        """説明文としきい値がずれると、凡例と地図の色が食い違う。"""

        for tone, label in tone_ranges()[:-1]:
            lower, upper = (int(n) for n in label.rstrip("日前").split("〜"))

            with self.subTest(tone=tone):
                self.assertEqual(tone, sighting_tone(lower))
                self.assertEqual(tone, sighting_tone(upper))
                self.assertNotEqual(tone, sighting_tone(upper + 1))

    def test_real_data_covers_more_than_one_tone(self):
        records = load_all_records(REAL_FILES)
        reference = reference_date(records)

        tones = {sighting_tone(days_ago(r, reference)) for r in records}

        self.assertGreater(len(tones), 1)


class PeriodFilterTest(unittest.TestCase):
    def setUp(self):
        self.reference = datetime(2026, 8, 5)
        self.records = [
            make_record("2026/8/5"),
            make_record("2026/8/1"),
            make_record("2026/7/20"),
            make_record("2026/3/30"),
            make_record("読めない日付"),
        ]

    def test_choices_are_the_four_in_the_spec(self):
        self.assertEqual(("直近7日", "直近30日", "今季", "すべて"), PERIOD_CHOICES)

    def test_all_keeps_every_record_including_unreadable_dates(self):
        self.assertEqual(5, len(filter_by_period(self.records, PERIOD_ALL, self.reference)))

    def test_seven_days_counts_the_reference_day_as_the_first(self):
        """基準日を1日目として7日分。経過日数0〜6が入る。"""

        kept = filter_by_period(self.records, PERIOD_7, self.reference)

        self.assertEqual(["2026/8/5", "2026/8/1"], [r["年月日"] for r in kept])

    def test_thirty_days(self):
        kept = filter_by_period(self.records, PERIOD_30, self.reference)

        self.assertEqual(3, len(kept))

    def test_season_starts_at_the_first_of_april(self):
        kept = filter_by_period(self.records, PERIOD_SEASON, self.reference)

        self.assertNotIn("2026/3/30", [r["年月日"] for r in kept])
        self.assertEqual(3, len(kept))

    def test_unreadable_date_is_dropped_when_a_period_is_chosen(self):
        """置く場所を決められないため外す。「すべて」のときだけ残す。"""

        for period in (PERIOD_7, PERIOD_30, PERIOD_SEASON):
            with self.subTest(period=period):
                kept = filter_by_period(self.records, period, self.reference)
                self.assertNotIn("読めない日付", [r["年月日"] for r in kept])

    def test_season_start_uses_the_fiscal_year(self):
        self.assertEqual(datetime(2026, 4, 1), season_start(datetime(2026, 8, 5)))
        self.assertEqual(datetime(2025, 4, 1), season_start(datetime(2026, 3, 31)))

    def test_real_data_narrows_as_the_period_shortens(self):
        records = load_all_records(REAL_FILES)
        reference = reference_date(records)

        sizes = [
            len(filter_by_period(records, period, reference))
            for period in PERIOD_CHOICES
        ]

        self.assertEqual(sizes, sorted(sizes))
        self.assertEqual(len(records), sizes[-1])

    def test_record_date_parses_single_digit_months(self):
        self.assertEqual(datetime(2026, 4, 2), record_date(make_record("2026/4/2")))


class SortByDateTest(unittest.TestCase):
    def test_newest_comes_first(self):
        records = [
            {"No.": "1", "年月日": "2026/4/2"},
            {"No.": "2", "年月日": "2026/8/5"},
            {"No.": "3", "年月日": "2026/6/1"},
        ]

        self.assertEqual(
            ["2026/8/5", "2026/6/1", "2026/4/2"],
            [r["年月日"] for r in sort_by_date_desc(records)],
        )

    def test_same_date_is_ordered_by_number(self):
        """順番を決めておかないと、開くたびに並びが変わって見失う。"""

        records = [
            {"No.": "5", "年月日": "2026/8/5"},
            {"No.": "12", "年月日": "2026/8/5"},
            {"No.": "9", "年月日": "2026/8/5"},
        ]

        self.assertEqual(
            ["12", "9", "5"], [r["No."] for r in sort_by_date_desc(records)]
        )

    def test_unreadable_dates_go_last(self):
        records = [
            {"No.": "1", "年月日": "令和8年4月2日"},
            {"No.": "2", "年月日": "2026/8/5"},
            {"No.": "3", "年月日": ""},
        ]

        self.assertEqual(["2", "3", "1"], [r["No."] for r in sort_by_date_desc(records)])

    def test_the_original_list_is_left_alone(self):
        records = [
            {"No.": "1", "年月日": "2026/4/2"},
            {"No.": "2", "年月日": "2026/8/5"},
        ]

        sort_by_date_desc(records)

        self.assertEqual(["1", "2"], [r["No."] for r in records])

    def test_no_record_is_lost_or_duplicated(self):
        records = load_all_records(REAL_FILES)

        sorted_records = sort_by_date_desc(records)

        self.assertEqual(len(records), len(sorted_records))
        self.assertEqual(
            sorted(r["No."] for r in records),
            sorted(r["No."] for r in sorted_records),
        )

    def test_the_same_input_always_gives_the_same_order(self):
        records = load_all_records(REAL_FILES)

        first = [r["No."] for r in sort_by_date_desc(records)]
        second = [r["No."] for r in sort_by_date_desc(records)]

        self.assertEqual(first, second)

    def test_real_data_runs_from_newest_to_oldest(self):
        records = sort_by_date_desc(load_all_records(REAL_FILES))

        self.assertEqual("2026/8/5", records[0]["年月日"])
        self.assertEqual("2026/4/2", records[-1]["年月日"])

    def test_real_data_never_goes_back_in_time(self):
        records = sort_by_date_desc(load_all_records(REAL_FILES))
        dates = [record_date(r) for r in records]

        for newer, older in zip(dates, dates[1:]):
            self.assertGreaterEqual(newer, older)


class EmptyResultTest(unittest.TestCase):
    """0件の案内を出す条件を、画面ではなくデータ側で確かめる。"""

    def test_municipality_whose_only_sighting_has_no_usable_coordinates(self):
        records = load_all_records(REAL_FILES)
        mappable, unmappable = split_by_coordinates(records)

        shown = filter_by_municipality(mappable, "西桂町")
        hidden = filter_by_municipality(unmappable, "西桂町")

        self.assertEqual(0, len(shown))
        self.assertEqual(1, len(hidden))

    def test_every_unmappable_record_still_belongs_to_a_municipality(self):
        records = load_all_records(REAL_FILES)
        _, unmappable = split_by_coordinates(records)

        for record in unmappable:
            self.assertNotEqual("", record["目撃市町村"].strip())


if __name__ == "__main__":
    unittest.main()
