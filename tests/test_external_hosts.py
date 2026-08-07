"""画面に書いた「外部への通信先」が、実際と一致するかを確かめる。

プライバシーの説明は、書いた瞬間から古くなりうる。
foliumやstreamlit-foliumが読み込むものを増やしたり減らしたりすれば、
画面に書いた一覧は嘘になる。ここで気づけるようにする。

集め方は`streamlit_folium`と同じにする。
`_get_header`は`<script src>`や`<link>`を取り除くが、
それらは`css_links`/`js_links`として別途フロントエンドへ渡され、
ブラウザが読み込む。ヘッダーだけを見ると「通信しない」と誤解する。
"""

import html as html_module
import re
import unittest
from urllib.parse import urlparse

import folium
import folium.elements
from folium.plugins import MarkerCluster
from streamlit_folium import generate_leaflet_string

from map_overlays import MapControls, SightingListControl
from ui_styles import (
    CLUSTER_ICON_JS,
    CLUSTER_OPTIONS,
    EXTERNAL_HOSTS,
    MAP_STYLES,
    MAP_TILES,
    ZOOM_CONTROL_POSITION,
    MARKER_CLASS,
    MARKER_SIZE,
    bear_marker_svg,
    privacy_markdown,
    sighting_list_html,
)


def build_map() -> folium.Map:
    """app.pyと同じ組み立てをする。"""

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
    folium.Marker(
        location=(35.55, 138.59),
        icon=folium.DivIcon(
            html=bear_marker_svg(), icon_size=MARKER_SIZE, class_name=MARKER_CLASS
        ),
        **{"dataIndex": 0},
    ).add_to(pins)
    bear_map.add_child(MapControls(["目撃 1件"], (35.66, 138.57), 9))
    bear_map.add_child(SightingListControl(sighting_list_html([])))
    bear_map.get_root().render()
    bear_map.render()

    return bear_map


def linked_hosts(bear_map: folium.Map) -> set[str]:
    """`streamlit_folium`がフロントエンドへ渡すCSS/JSの通信先。"""

    def walk(node):
        if isinstance(node, folium.elements.JSCSSMixin):
            yield node
        for child in getattr(node, "_children", {}).values():
            yield from walk(child)

    urls = []
    for element in walk(bear_map):
        urls += [href for _, href in getattr(element, "default_css", [])]
        urls += [src for _, src in getattr(element, "default_js", [])]

    return {urlparse(url).netloc for url in urls if url.startswith("http")}


def tile_hosts(bear_map: folium.Map) -> set[str]:
    """地図タイルの通信先。`{s}`はサブドメインの置き場所なので取り除く。"""

    leaflet = html_module.unescape(generate_leaflet_string(bear_map))
    urls = re.findall(r'"(https://[^"]*\{[zxy]\}[^"]*)"', leaflet)

    return {urlparse(url).netloc.replace("{s}.", "") for url in urls}


class ExternalHostsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bear_map = build_map()
        cls.actual = linked_hosts(bear_map) | tile_hosts(bear_map)
        cls.documented = {host for host, _ in EXTERNAL_HOSTS}

    def test_nothing_undocumented_is_contacted(self):
        """画面に書いていない相手へ通信していないか。"""

        undocumented = self.actual - self.documented

        self.assertEqual(
            set(),
            undocumented,
            f"画面に書いていない通信先がある: {sorted(undocumented)}",
        )

    def test_nothing_documented_is_unused(self):
        """使っていない相手を書いていないか。多く書けばよいものでもない。"""

        unused = self.documented - self.actual

        self.assertEqual(
            set(), unused, f"実際には通信していない相手を書いている: {sorted(unused)}"
        )

    def test_the_tile_server_is_contacted(self):
        """地図タイルは地図を動かすたびに読み込む。抜けやすいので個別に見る。"""

        self.assertIn("basemaps.cartocdn.com", self.actual)

    def test_the_privacy_text_lists_exactly_these_hosts(self):
        text = privacy_markdown()

        for host in self.actual:
            with self.subTest(host=host):
                self.assertIn(host, text)

    def test_the_count_matches_what_we_tell_people(self):
        self.assertEqual(len(EXTERNAL_HOSTS), len(self.actual))


class CollectionMethodTest(unittest.TestCase):
    """集め方が`streamlit_folium`と食い違っていないかの番人。"""

    def test_streamlit_folium_still_passes_links_separately(self):
        """`css_links`/`js_links`で渡す作りが変わったら、集め方を見直す。"""

        import streamlit_folium
        from pathlib import Path

        source = Path(streamlit_folium.__file__).read_text(encoding="utf-8")

        self.assertIn("css_links=css_links", source)
        self.assertIn("js_links=js_links", source)
        self.assertIn('getattr(elem, "default_css", [])', source)

    def test_the_header_alone_would_be_misleading(self):
        """ヘッダーからはタグが取り除かれる。ヘッダーだけ見て判断しない。"""

        from streamlit_folium import _get_header

        header = _get_header(build_map())

        self.assertEqual(0, len(re.findall(r"<script[^>]*src=", header)))


if __name__ == "__main__":
    unittest.main()
