"""地図の上に出す目撃の一覧を確かめる。"""

import html as html_module
import re
import unittest

import folium

from map_overlays import MARKER_INDEX_OPTION, SightingListControl
from ui_styles import (
    BREAKPOINT_MOBILE,
    LIST_CLASS,
    LIST_EMPTY_TEXT,
    LIST_OPEN_CLASS,
    MAP_STYLES,
    TONE_COLORS,
    sighting_list_html,
)


def make_rows(count: int) -> list[dict[str, object]]:
    tones = list(TONE_COLORS)

    return [
        {
            "index": i,
            "date": "2026/8/5",
            "recency": "当日",
            "municipality": "身延町",
            "place": "相又地内",
            "tone": tones[i % len(tones)],
        }
        for i in range(count)
    ]


class ListContentTest(unittest.TestCase):
    def test_every_row_is_rendered(self):
        """件数が多いからといって黙って打ち切らない。"""

        html = sighting_list_html(make_rows(156))

        self.assertEqual(156, html.count(f'class="{LIST_CLASS}__row"'))

    def test_the_heading_count_matches_the_rows(self):
        """見出しと中身が食い違わないよう、件数は行から数える。"""

        for count in (0, 1, 11, 156):
            with self.subTest(count=count):
                html = sighting_list_html(make_rows(count))

                self.assertIn(f"目撃 {count}件", html)
                self.assertEqual(count, html.count(f'class="{LIST_CLASS}__row"'))

    def test_a_row_shows_date_recency_municipality_and_place(self):
        html = sighting_list_html(
            [
                {
                    "index": 3,
                    "date": "2026/7/30",
                    "recency": "6日前",
                    "municipality": "北杜市",
                    "place": "武川町黒澤地内",
                    "tone": "mid",
                }
            ]
        )

        self.assertIn("2026/7/30", html)
        self.assertIn("6日前", html)
        self.assertIn("北杜市", html)
        self.assertIn("武川町黒澤地内", html)

    def test_the_dot_uses_the_tone_colour(self):
        html = sighting_list_html(
            [
                {
                    "index": 0,
                    "date": "2026/8/5",
                    "recency": "当日",
                    "municipality": "身延町",
                    "place": "相又地内",
                    "tone": "recent",
                }
            ]
        )

        self.assertIn(f'background:{TONE_COLORS["recent"]}', html)

    def test_empty_result_says_so(self):
        html = sighting_list_html([])

        self.assertIn(LIST_EMPTY_TEXT, html)
        self.assertIn("目撃 0件", html)
        self.assertNotIn(f'class="{LIST_CLASS}__row"', html)


class ListSafetyTest(unittest.TestCase):
    def test_free_text_is_escaped(self):
        html = sighting_list_html(
            [
                {
                    "index": 0,
                    "date": "2026/8/5",
                    "recency": "当日",
                    "municipality": '<script>alert("x")</script>',
                    "place": "地内",
                    "tone": "recent",
                }
            ]
        )

        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_the_index_is_forced_to_a_number(self):
        """`data-index`から属性を抜け出せないようにする。"""

        html = sighting_list_html(
            [
                {
                    "index": "7",
                    "date": "2026/8/5",
                    "recency": "当日",
                    "municipality": "身延町",
                    "place": "相又地内",
                    "tone": "recent",
                }
            ]
        )

        self.assertIn('data-index="7"', html)

        with self.assertRaises(ValueError):
            sighting_list_html(
                [
                    {
                        "index": '0" onclick="alert(1)',
                        "date": "2026/8/5",
                        "recency": "当日",
                        "municipality": "身延町",
                        "place": "相又地内",
                        "tone": "recent",
                    }
                ]
            )

    def test_indexes_are_kept_in_order(self):
        html = sighting_list_html(make_rows(5))

        found = re.findall(r'data-index="(\d+)"', html)

        self.assertEqual(["0", "1", "2", "3", "4"], found)


class ListStyleTest(unittest.TestCase):
    def test_styles_are_inside_the_map(self):
        """`st.markdown`のCSSはiframeを越えない。地図側に入れる。"""

        self.assertIn(f".{LIST_CLASS} {{", MAP_STYLES)
        self.assertIn(f".{LIST_CLASS}__row {{", MAP_STYLES)

    def test_rows_are_44px_tap_targets(self):
        row = MAP_STYLES.split(f".{LIST_CLASS}__row {{")[1].split("}")[0]
        head = MAP_STYLES.split(f".{LIST_CLASS}__head {{")[1].split("}")[0]

        self.assertIn("min-height: 44px;", row)
        self.assertIn("min-height: 44px;", head)

    def test_long_lists_scroll_instead_of_overflowing(self):
        items = MAP_STYLES.split(f".{LIST_CLASS}__items {{")[1].split("}")[0]

        self.assertIn("overflow-y: auto;", items)
        self.assertIn("max-height:", items)

    def test_the_body_is_hidden_until_the_open_class_is_set(self):
        """開閉はクラスの付け外しで行う。動かすのはL-003。"""

        body = MAP_STYLES.split(f".{LIST_CLASS}__body {{")[1].split("}")[0]

        self.assertIn("display: none;", body)
        self.assertIn(f".{LIST_OPEN_CLASS} .{LIST_CLASS}__body {{", MAP_STYLES)

    def test_text_and_background_are_set_together(self):
        for selector in (f".{LIST_CLASS}__row {{", f".{LIST_CLASS}__head {{"):
            block = MAP_STYLES.split(selector)[1].split("}")[0]

            with self.subTest(selector=selector):
                self.assertIn("background:", block)
                self.assertIn("color:", block)


def render_control(rows) -> str:
    """地図へ一覧を足し、組み立てられたJavaScriptを返す。"""

    bear_map = folium.Map(location=(35.66, 138.57), zoom_start=9)
    bear_map.add_child(SightingListControl(sighting_list_html(rows)))

    return html_module.unescape(bear_map._repr_html_())


class ListControlTest(unittest.TestCase):
    def setUp(self):
        self.js = render_control(make_rows(3))

    def test_the_list_sits_in_the_top_right(self):
        self.assertIn("position: 'topright'", self.js)
        self.assertIn("map.addControl(new List());", self.js)

    def test_clicks_and_scrolling_do_not_reach_the_map(self):
        """行を押したつもりで地図が動いたり、一覧を送ったつもりで地図がずれたりしない。"""

        self.assertIn("L.DomEvent.disableClickPropagation(box);", self.js)
        self.assertIn("L.DomEvent.disableScrollPropagation(box);", self.js)

    def test_the_heading_toggles_the_list(self):
        self.assertIn(f"classList.toggle('{LIST_OPEN_CLASS}')", self.js)

    def test_the_toggle_tells_assistive_tech(self):
        """開閉の状態は見た目だけでなく`aria-expanded`でも伝える。"""

        self.assertIn("head.setAttribute('aria-expanded'", self.js)

    def test_japanese_survives_the_embedding(self):
        js = render_control(
            [
                {
                    "index": 0,
                    "date": "2026/8/5",
                    "recency": "当日",
                    "municipality": "身延町",
                    "place": "相又地内",
                    "tone": "recent",
                }
            ]
        )

        self.assertIn("身延町", js)
        self.assertNotIn(r"\u8eab", js)

    def test_quotes_in_the_html_do_not_break_the_script(self):
        """HTMLは引用符だらけ。素朴に埋め込むとJavaScriptが壊れる。"""

        self.assertIn('box.innerHTML = "<div class=\\"', self.js)

    def test_the_wrapper_has_no_leaflet_box_of_its_own(self):
        wrapper = MAP_STYLES.split(f".{LIST_CLASS}-wrapper {{")[1].split("}")[0]

        self.assertIn("background: transparent;", wrapper)
        self.assertIn("border: 0;", wrapper)


class RowClickTest(unittest.TestCase):
    def setUp(self):
        self.js = render_control(make_rows(3))

    def test_a_click_anywhere_in_the_row_counts(self):
        """行の中の文字を押しても、行を押したものとして扱う。"""

        self.assertIn(f"event.target.closest('.{LIST_CLASS}__row')", self.js)

    def test_the_marker_is_found_by_its_index_not_by_a_variable_name(self):
        """変数名は`streamlit-folium`が付け替える。名前に頼らない。"""

        self.assertIn(f"options.{MARKER_INDEX_OPTION} === index", self.js)
        self.assertNotIn("var markers = [marker_", self.js)

    def test_the_cluster_is_found_at_runtime(self):
        self.assertIn("if (layer.zoomToShowLayer) { found = layer; }", self.js)

    def test_a_marker_inside_a_cluster_is_opened(self):
        """クラスタにまとまったピンは、展開しないと吹き出しを開けない。"""

        self.assertIn("cluster.zoomToShowLayer(marker, function () { marker.openPopup(); });", self.js)

    def test_it_still_works_without_a_cluster(self):
        self.assertIn("if (cluster && cluster.zoomToShowLayer) {", self.js)
        self.assertIn("} else {", self.js)

    def test_an_unknown_index_is_ignored(self):
        self.assertIn("if (!marker) { return; }", self.js)

    def test_the_chosen_row_is_marked(self):
        """どの行を開いたかが分かるようにする。色以外の手がかりでもある。"""

        self.assertIn("row.setAttribute('aria-current', 'true');", self.js)
        self.assertIn("other.removeAttribute('aria-current');", self.js)

    def test_an_empty_list_still_builds(self):
        js = render_control([])

        self.assertIn("map.addControl(new List());", js)
        self.assertIn(LIST_EMPTY_TEXT, js)


class NarrowScreenTest(unittest.TestCase):
    def setUp(self):
        self.js = render_control(make_rows(3))

    def test_the_list_closes_itself_on_a_narrow_map(self):
        """開いたままだと地図が隠れる。指示書§17の767pxで閉じる。"""

        self.assertIn(f"if (width <= {BREAKPOINT_MOBILE}) {{", self.js)
        self.assertIn(f"panel.classList.remove('{LIST_OPEN_CLASS}');", self.js)

    def test_closing_it_also_updates_aria(self):
        """見た目だけ閉じて`aria-expanded`が開いたままだと、読み上げと食い違う。"""

        self.assertIn("head.setAttribute('aria-expanded', 'false');", self.js)

    def test_the_width_comes_from_the_map_not_the_page(self):
        """地図はiframeの中にある。ページ全体の幅で判定すると合わない。"""

        self.assertIn("map.getSize().x || window.innerWidth", self.js)

    def test_the_list_never_outgrows_the_map(self):
        items = MAP_STYLES.split(f".{LIST_CLASS}__items {{")[1].split("}")[0]

        self.assertIn("max-height: min(380px, 58vh);", items)


if __name__ == "__main__":
    unittest.main()
