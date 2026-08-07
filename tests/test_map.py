"""地図そのものの決まりごとを確かめる。

`app.py`はStreamlitのスクリプトなので、そのままではimportできない。
ここでは`app.py`と同じ設定でfoliumの地図を組み立て、生成されるHTMLを調べる。
"""

import html as html_module
import unittest
from pathlib import Path

import folium

from folium.plugins import MarkerCluster

from map_overlays import MapControls
from ui_styles import (
    CLUSTER_CLASS,
    CLUSTER_ICON_JS,
    CLUSTER_OPTIONS,
    CLUSTER_TIERS,
    FIT_MAX_ZOOM,
    FIT_PADDING,
    MAP_STYLES,
    MAP_TILES,
    MARKER_CLASS,
    MARKER_SIZE,
    POPUP_CLASS,
    POPUP_MAX_WIDTH,
    ZOOM_CONTROL_POSITION,
    bear_marker_svg,
    popup_card_html,
)


SAMPLE_DETAILS = [
    ("日付", "2026/8/5"),
    ("時間", "17:20"),
    ("場所", "右左口町"),
    ("状況", "沢にいた。避難したためその後は不明"),
    ("人身被害", "無し"),
]
SOURCE_LABEL = "出典：山梨県 森林環境部 自然共生推進課"


ROOT = Path(__file__).resolve().parent.parent


def build_map(with_marker: bool = False) -> str:
    """app.pyと同じ設定で地図を組み立て、HTMLを返す。"""

    bear_map = folium.Map(
        location=(35.66, 138.57),
        zoom_start=9,
        tiles=MAP_TILES,
        scroll_wheel_zoom=False,
        zoom_snap=1,
        zoom_delta=1,
    )
    bear_map.get_root().header.add_child(folium.Element(MAP_STYLES))

    if with_marker:
        pins = MarkerCluster(
            icon_create_function=CLUSTER_ICON_JS,
            options=CLUSTER_OPTIONS,
        ).add_to(bear_map)
        folium.Marker(
            location=(35.55, 138.59),
            icon=folium.DivIcon(
                html=bear_marker_svg(),
                icon_size=MARKER_SIZE,
                icon_anchor=(MARKER_SIZE[0] // 2, MARKER_SIZE[1] - 2),
                popup_anchor=(0, -MARKER_SIZE[1] + 4),
                class_name=MARKER_CLASS,
            ),
            tooltip="甲府市 2026/4/2",
        ).add_to(pins)

    return html_module.unescape(bear_map._repr_html_())


def render_overlay(overlay) -> str:
    """地図へ部品を足し、組み立てられたJavaScriptを返す。

    部品は地図の子要素にしないと`streamlit-folium`に届かない。
    届く形かどうかは`tests/test_streamlit_render.py`で確かめる。
    """

    bear_map = folium.Map(location=(35.66, 138.57), zoom_start=9, tiles=MAP_TILES)
    bear_map.add_child(overlay)

    return html_module.unescape(bear_map._repr_html_())


class TileTest(unittest.TestCase):
    def setUp(self):
        self.html = build_map()

    def test_muted_tiles_are_used(self):
        """OpenStreetMap標準タイルではなく、淡いタイルを使う。"""

        self.assertIn("basemaps.cartocdn.com", self.html)
        self.assertNotIn("https://tile.openstreetmap.org", self.html)

    def test_attribution_is_kept(self):
        """出典表示は消さない。利用規約とタイル提供者の両方の要求。"""

        self.assertIn("OpenStreetMap", self.html)
        self.assertIn("CARTO", self.html)

    def test_no_new_dependency_was_added(self):
        """タイル変更で依存が増えていないこと。UI改善は追加インストールなしで進める。"""

        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        packages = [line for line in requirements.splitlines() if line.strip()]

        self.assertEqual(3, len(packages))
        self.assertTrue(any(line.startswith("streamlit>") for line in packages))
        self.assertTrue(any(line.startswith("folium") for line in packages))
        self.assertTrue(any(line.startswith("streamlit-folium") for line in packages))


class WheelZoomTest(unittest.TestCase):
    def test_scroll_wheel_zoom_stays_disabled(self):
        """T-010で無効化した設定を、UI改善で戻してしまわないための番人。"""

        self.assertIn('"scrollWheelZoom": false', build_map())


class MarkerTest(unittest.TestCase):
    def setUp(self):
        self.svg = bear_marker_svg()
        self.html = build_map(with_marker=True)

    def test_marker_is_an_svg_pin(self):
        self.assertTrue(self.svg.startswith("<svg"))
        self.assertIn("<path", self.svg)
        self.assertEqual((36, 42), MARKER_SIZE)

    def test_marker_has_a_paw_inside(self):
        """涙型の中に足跡を入れる。丸5つで描いている。"""

        self.assertEqual(5, self.svg.count("<ellipse"))

    def test_marker_uses_no_emoji(self):
        for emoji in ("🐻", "🐾", "📍", "🔴"):
            self.assertNotIn(emoji, self.svg)

    def test_marker_loads_no_external_image(self):
        """CDNの画像を読まない。T-010のリンク切れを繰り返さない。"""

        self.assertNotIn("<img", self.svg)
        self.assertNotIn("marker-icon.png", self.html)
        self.assertNotIn("AwesomeMarkers.icon", self.html)

    def test_circle_marker_is_gone(self):
        """赤い丸マーカーへ戻さない（指示書§23）。"""

        self.assertNotIn("circleMarker", self.html)
        self.assertNotIn("#d93025", self.html.lower())

    def test_marker_colour_comes_from_the_palette(self):
        from ui_styles import COLORS

        self.assertIn(COLORS["brand"], self.svg)

    def test_marker_can_be_recoloured(self):
        """U-011で経過日数ごとの色に差し替えられること。"""

        from ui_styles import TONE_COLORS

        self.assertIn(TONE_COLORS["recent"], bear_marker_svg(TONE_COLORS["recent"]))


class ClusterTest(unittest.TestCase):
    def setUp(self):
        self.html = build_map(with_marker=True)

    def test_clustering_is_enabled(self):
        self.assertIn("markerClusterGroup", self.html)

    def test_cluster_uses_our_own_icon(self):
        """Leaflet既定の緑・黄・赤の丸は使わない。"""

        self.assertIn(f'{CLUSTER_CLASS}-wrapper', self.html)
        self.assertNotIn("marker-cluster-small", self.html)
        self.assertNotIn("marker-cluster-large", self.html)

    def test_each_tier_has_its_own_diameter(self):
        sizes = [tier[2] for tier in CLUSTER_TIERS]

        self.assertEqual(3, len(set(sizes)))
        self.assertEqual(sizes, sorted(sizes))

    def test_tier_rules_change_size_only_not_colour(self):
        """件数が多いほど赤くなる既定の見せ方はしない。多い＝危険ではない（指示書§10）。"""

        for tier_name, _, _ in CLUSTER_TIERS:
            rule = MAP_STYLES.split(f".{CLUSTER_CLASS}--{tier_name} {{")[1].split("}")[0]

            with self.subTest(tier=tier_name):
                self.assertIn("font-size", rule)
                self.assertNotIn("background", rule)
                self.assertNotIn("color", rule)

    def test_tier_boundaries_follow_the_spec(self):
        """1〜9がsmall、10〜49がmedium、50以上がlarge。"""

        self.assertEqual(("small", 10, 38), CLUSTER_TIERS[0])
        self.assertEqual(("medium", 50, 46), CLUSTER_TIERS[1])
        self.assertEqual("large", CLUSTER_TIERS[2][0])
        self.assertIsNone(CLUSTER_TIERS[2][1])

    def test_click_opens_the_cluster(self):
        self.assertTrue(CLUSTER_OPTIONS["zoomToBoundsOnClick"])
        self.assertTrue(CLUSTER_OPTIONS["spiderfyOnMaxZoom"])

    def test_hover_polygon_is_off(self):
        """ホバーで範囲の多角形を出す既定の動きは、地図が騒がしくなるので切る。"""

        self.assertFalse(CLUSTER_OPTIONS["showCoverageOnHover"])
        self.assertIn('"showCoverageOnHover": false', self.html)


class PopupCardTest(unittest.TestCase):
    def setUp(self):
        self.html = popup_card_html("甲府市", SAMPLE_DETAILS, SOURCE_LABEL)

    def test_required_items_are_shown(self):
        """指示書§11の必須5項目。日時・市町村・場所・内容・情報ソース。"""

        self.assertIn("2026/8/5 17:20", self.html)
        self.assertIn("甲府市", self.html)
        self.assertIn("右左口町", self.html)
        self.assertIn("沢にいた。", self.html)
        self.assertIn("自然共生推進課", self.html)

    def test_injury_column_is_kept(self):
        """PROJECT.mdの完成条件にある5項目のひとつ。省かない。"""

        self.assertIn("人身被害", self.html)
        self.assertIn("無し", self.html)

    def test_free_text_is_escaped(self):
        details = [*SAMPLE_DETAILS[:3], ("状況", '<script>alert("x")</script>'), SAMPLE_DETAILS[4]]

        html = popup_card_html("甲府市", details, SOURCE_LABEL)

        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_recency_is_shown_in_words(self):
        """色が読めなくても経過が分かるようにする（指示書§18）。"""

        html = popup_card_html("甲府市", SAMPLE_DETAILS, SOURCE_LABEL, "2日前")

        self.assertIn("2日前", html)
        self.assertIn(f"{POPUP_CLASS}__recency", html)

    def test_recency_is_omitted_when_not_given(self):
        self.assertNotIn(f"{POPUP_CLASS}__recency", self.html)

    def test_missing_time_does_not_leave_a_stray_space(self):
        details = [("日付", "2026/5/7"), ("時間", ""), *SAMPLE_DETAILS[2:]]

        html = popup_card_html("山梨市", details, SOURCE_LABEL)

        self.assertIn(f'__when">2026/5/7<', html)


class LeafletOverrideTest(unittest.TestCase):
    def test_popup_is_not_the_default_leaflet_look(self):
        """既定の角丸12px・白背景のままにしない。"""

        self.assertIn(".leaflet-popup-content-wrapper {", MAP_STYLES)
        self.assertIn("border-radius: 16px;", MAP_STYLES)
        self.assertIn(".leaflet-popup-tip {", MAP_STYLES)

    def test_popup_width_is_within_the_spec(self):
        """指示書§11は280〜320px。"""

        self.assertEqual(320, POPUP_MAX_WIDTH)
        self.assertIn(f"max-width: {POPUP_MAX_WIDTH}px;", MAP_STYLES)

    def test_close_button_is_a_44px_tap_target(self):
        self.assertIn("width: 44px !important;", MAP_STYLES)
        self.assertIn("height: 44px !important;", MAP_STYLES)

    def test_zoom_buttons_are_restyled(self):
        self.assertIn(".leaflet-bar a,", MAP_STYLES)
        self.assertIn(f".{POPUP_CLASS} {{", MAP_STYLES)

    def test_attribution_is_styled_but_not_hidden(self):
        """出典表示は消さない。読みやすくするだけ。"""

        rule = MAP_STYLES.split(".leaflet-control-attribution {")[1].split("}")[0]

        self.assertIn("background:", rule)
        self.assertNotIn("display: none", rule)
        self.assertNotIn("visibility: hidden", rule)
        self.assertNotIn("opacity: 0", rule)


class MapControlsTest(unittest.TestCase):
    """地図の上の操作。`streamlit-folium`に届く形かは`test_streamlit_render.py`で見る。"""

    def setUp(self):
        self.js = render_overlay(MapControls(["目撃 156件", "今季", "甲府市"], (35.66, 138.57), 9))

    def test_japanese_is_not_turned_into_escape_sequences(self):
        self.assertIn("目撃 156件", self.js)
        self.assertNotIn(r"\u76ee", self.js)

    def test_quotes_in_a_name_do_not_break_the_script(self):
        """市町村名をそのまま埋め込むと、引用符でJavaScriptが壊れる。"""

        js = render_overlay(MapControls(['甲府"市'], (35.6, 138.5), 9))

        self.assertNotIn('<span class="map-chip">甲府"市</span>";', js)
        self.assertIn("&quot;", js)

    def test_home_button_returns_to_the_given_view(self):
        self.assertIn("map.setView([35.66, 138.57], 9)", self.js)
        self.assertIn("山梨全体へ戻る", self.js)

    def test_chips_have_no_close_button(self):
        """地図はiframeの中にあり、そこからStreamlitの選択は変えられない。
        押せないボタンは置かない。解除は地図の外のボタンで行う。"""

        self.assertNotIn("×", self.js)
        self.assertNotIn("map-chip__close", self.js)

    def test_the_map_is_referenced_by_its_rendered_name(self):
        """名前を自分で組み立てない。`streamlit-folium`が付け替えるため。"""

        self.assertIn("var map = ", self.js)
        self.assertNotIn("{{", self.js)

    def test_zoom_control_moves_to_the_bottom_right(self):
        bear_map = folium.Map(
            location=(35.66, 138.57),
            zoom_start=9,
            tiles=MAP_TILES,
            zoom_control=ZOOM_CONTROL_POSITION,
        )
        html = html_module.unescape(bear_map._repr_html_())

        self.assertEqual("bottomright", ZOOM_CONTROL_POSITION)
        self.assertIn('L.control.zoom( { position: "bottomright" } )', html)
        self.assertIn('"zoomControl": false', html)

    def test_chip_styles_are_inside_the_map(self):
        """ページ側のCSHはiframeを越えない。地図側に入っていること。"""

        self.assertIn(".map-chip {", MAP_STYLES)
        self.assertIn(".map-home a {", MAP_STYLES)


class FitBoundsTest(unittest.TestCase):
    """市町村を選んだときの表示範囲。app.pyと同じ呼び方で確かめる。"""

    def build(self, bounds):
        bear_map = folium.Map(
            location=(35.66, 138.57), zoom_start=9, tiles=MAP_TILES
        )
        if bounds:
            bear_map.fit_bounds(bounds, padding=FIT_PADDING, max_zoom=FIT_MAX_ZOOM)

        return html_module.unescape(bear_map._repr_html_())

    def test_bounds_are_passed_to_the_map(self):
        html = self.build([[35.4, 138.4], [35.6, 138.7]])

        self.assertIn("fitBounds", html)
        self.assertIn("[35.4, 138.4]", html)
        self.assertIn("[35.6, 138.7]", html)

    def test_zoom_has_an_upper_limit(self):
        """1件だけの市町村で限界まで寄ってしまうのを防ぐ。"""

        html = self.build([[35.5, 138.6], [35.5, 138.6]])

        self.assertIn("fitBounds", html)
        self.assertIn(f'"maxZoom": {FIT_MAX_ZOOM}', html)

    def test_padding_keeps_pins_off_the_edge(self):
        html = self.build([[35.4, 138.4], [35.6, 138.7]])

        self.assertIn(f'"padding": [{FIT_PADDING[0]}, {FIT_PADDING[1]}]', html)

    def test_no_bounds_leaves_the_whole_prefecture_visible(self):
        html = self.build(None)

        self.assertNotIn("fitBounds", html)
        self.assertIn("[35.66, 138.57]", html)


class MapStylesTest(unittest.TestCase):
    def test_styles_reach_the_map_iframe(self):
        """`st.markdown`のCSSはiframeを越えない。地図側に入っていること。"""

        self.assertIn(f".{MARKER_CLASS}__svg", build_map())

    def test_hover_enlarges_the_marker(self):
        self.assertIn(f".{MARKER_CLASS}:hover", MAP_STYLES)
        self.assertIn("transform: scale(1.11);", MAP_STYLES)

    def test_reduced_motion_is_respected(self):
        """指示書§18の必須項目。動きを減らす設定を尊重する。"""

        self.assertIn("prefers-reduced-motion: reduce", MAP_STYLES)

    def test_focus_is_visible_for_keyboard_users(self):
        self.assertIn("focus-visible", MAP_STYLES)


if __name__ == "__main__":
    unittest.main()
