"""`st_folium`が実際に画面へ送る中身を確かめる。

foliumの`_repr_html_()`に入っていても、画面に出るとは限らない。
`streamlit-folium`は地図のHTMLをそのまま渡さず、
地図オブジェクトの子要素をたどってJavaScriptを組み立て直すため、
`get_root().script`へ足したものは届かない。

一度この見落としで、一覧・チップ・「山梨全体へ戻る」が
画面に出ないまま完成扱いになった。同じことを繰り返さないための番人。
"""

import unittest

import folium
from folium.plugins import MarkerCluster
from streamlit_folium import _get_header, _get_html, generate_leaflet_string

from map_overlays import MARKER_INDEX_OPTION, MapControls, SightingListControl
from ui_styles import (
    CLUSTER_ICON_JS,
    CLUSTER_OPTIONS,
    HOME_LABEL,
    LIST_CLASS,
    MAP_STYLES,
    MAP_TILES,
    MARKER_CLASS,
    MARKER_SIZE,
    ZOOM_CONTROL_POSITION,
    bear_marker_svg,
    sighting_list_html,
)


ROWS = [
    {
        "index": 0,
        "date": "2026/8/5",
        "recency": "当日",
        "municipality": "身延町",
        "place": "相又地内",
        "tone": "recent",
    },
    {
        "index": 1,
        "date": "2026/8/4",
        "recency": "1日前",
        "municipality": "中央市",
        "place": "高部地内",
        "tone": "recent",
    },
]


def sent_to_the_browser() -> str:
    """app.pyと同じ手順で地図を組み立て、st_foliumが送る文字列を返す。"""

    bear_map = folium.Map(
        location=(35.66, 138.57),
        zoom_start=9,
        tiles=MAP_TILES,
        scroll_wheel_zoom=False,
        zoom_snap=1,
        zoom_delta=1,
        zoom_control=ZOOM_CONTROL_POSITION,
    )
    bear_map.get_root().header.add_child(folium.Element(MAP_STYLES))
    pins = MarkerCluster(
        icon_create_function=CLUSTER_ICON_JS, options=CLUSTER_OPTIONS
    ).add_to(bear_map)

    for index, row in enumerate(ROWS):
        folium.Marker(
            location=(35.5 + index / 100, 138.6),
            icon=folium.DivIcon(
                html=bear_marker_svg(),
                icon_size=MARKER_SIZE,
                class_name=MARKER_CLASS,
            ),
            tooltip=row["municipality"],
            **{MARKER_INDEX_OPTION: index},
        ).add_to(pins)

    bear_map.add_child(MapControls(["目撃 2件", "今季"], (35.66, 138.57), 9))
    bear_map.add_child(SightingListControl(sighting_list_html(ROWS)))

    bear_map.get_root().render()
    bear_map.render()

    return (
        _get_header(bear_map)
        + _get_html(bear_map)
        + generate_leaflet_string(bear_map)
    )


class SentToTheBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sent = sent_to_the_browser()

    def test_the_list_html_is_sent(self):
        self.assertIn("相又地内", self.sent)
        self.assertIn("高部地内", self.sent)
        self.assertIn("目撃 2件", self.sent)

    def test_the_list_control_is_added_to_the_map(self):
        self.assertIn("map.addControl(new List());", self.sent)

    def test_the_chips_are_added_to_the_map(self):
        self.assertIn("map.addControl(new Chips());", self.sent)
        self.assertIn("今季", self.sent)

    def test_the_home_button_is_added_to_the_map(self):
        self.assertIn("map.addControl(new Home());", self.sent)
        self.assertIn(HOME_LABEL, self.sent)

    def test_the_row_click_handler_is_sent(self):
        self.assertIn(f"event.target.closest('.{LIST_CLASS}__row')", self.sent)
        self.assertIn("cluster.zoomToShowLayer(marker", self.sent)

    def test_markers_carry_the_index_instead_of_a_variable_name(self):
        """変数名は`streamlit-folium`が付け替える。名前に頼らず値で探す。"""

        self.assertIn(f'"{MARKER_INDEX_OPTION}": 0', self.sent)
        self.assertIn(f'"{MARKER_INDEX_OPTION}": 1', self.sent)
        self.assertIn(f"options.{MARKER_INDEX_OPTION} === index", self.sent)

    def test_the_styles_are_sent(self):
        self.assertIn(f".{LIST_CLASS}__row", self.sent)
        self.assertIn(".map-chip", self.sent)

    def test_the_map_variable_is_referenced_by_its_rendered_name(self):
        """テンプレートが`this._parent.get_name()`を使っているか。
        自分で名前を組み立てると、付け替えのあとで合わなくなる。"""

        self.assertIn("var map = map_div;", self.sent)

    def test_the_cluster_is_found_at_runtime(self):
        self.assertIn("if (layer.zoomToShowLayer) { found = layer; }", self.sent)

    def test_no_leftover_script_tag_wrapping(self):
        """`MacroElement`の中身は素のJavaScript。`<script>`で包むと動かない。"""

        self.assertNotIn("<script>(function () {  function setup()", self.sent)


if __name__ == "__main__":
    unittest.main()
