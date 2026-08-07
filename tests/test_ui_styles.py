import re
import unittest

from ui_styles import (
    BREAKPOINT_MOBILE,
    BREAKPOINT_TABLET,
    COLORS,
    MAP_HEIGHT,
    PAGE_STYLES,
    PAW_SVG,
    RADIUS,
    SIDEBAR_WIDTH,
    SIDEBAR_WIDTH_TABLET,
    SPACE,
    TONE_COLORS,
    design_tokens_css,
    header_brand_html,
    header_meta_html,
    legend_html,
    note_html,
    summary_html,
)


HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


class DesignTokenTest(unittest.TestCase):
    def test_every_color_is_a_hex_value(self):
        for name, value in {**COLORS, **TONE_COLORS}.items():
            with self.subTest(name=name):
                self.assertRegex(value, HEX_COLOR)

    def test_four_tones_exist_for_marker_colors(self):
        """マーカーの色分けは4段階。凡例と食い違わないよう名前を固定する。"""

        self.assertEqual(
            ["recent", "mid", "older", "oldest"], list(TONE_COLORS.keys())
        )

    def test_tone_colors_are_all_different(self):
        self.assertEqual(len(TONE_COLORS), len(set(TONE_COLORS.values())))

    def test_pure_red_is_not_used(self):
        """指示書のとおり、真っ赤な色は使わない。"""

        for value in TONE_COLORS.values():
            self.assertNotIn(value.upper(), {"#FF0000", "#F00000", "#E60000"})

    def test_tokens_appear_as_css_variables(self):
        css = design_tokens_css()

        self.assertIn("--brand: #315B45;", css)
        self.assertIn("--tone-recent: #D95D39;", css)
        self.assertIn(f"--radius-md: {RADIUS['md']};", css)
        self.assertIn(f"--space-4: {SPACE['4']};", css)


class PageStylesTest(unittest.TestCase):
    def test_styles_are_wrapped_in_a_style_tag(self):
        self.assertTrue(PAGE_STYLES.startswith("<style>"))
        self.assertTrue(PAGE_STYLES.endswith("</style>"))

    def test_center_fixed_width_is_released(self):
        """中央固定幅をやめる指定が残っているか。地図の横幅に直結する。"""

        self.assertIn("max-width: 100%", PAGE_STYLES)
        self.assertIn(".block-container", PAGE_STYLES)

    def test_nothing_is_hidden_from_the_page(self):
        """Streamlitのヘッダーを消すとサイドバーを開けなくなる。何も隠さない。"""

        self.assertIn('[data-testid="stHeader"]', PAGE_STYLES)
        self.assertNotIn("display: none", PAGE_STYLES)
        self.assertNotIn("visibility: hidden", PAGE_STYLES)

    def test_h1_is_not_huge(self):
        self.assertIn("font-size: 22px !important;", PAGE_STYLES)


class HeaderTest(unittest.TestCase):
    def test_paw_icon_is_svg_and_not_emoji(self):
        """指示書のとおり、アイコンにemojiは使わない。"""

        self.assertTrue(PAW_SVG.startswith("<svg"))
        self.assertIn('aria-label="クマの足跡"', PAW_SVG)
        self.assertNotIn("🐻", PAW_SVG)
        self.assertNotIn("🐾", PAW_SVG)

    def test_brand_shows_the_icon_and_the_title_together(self):
        html = header_brand_html("山梨クマ目撃マップ")

        self.assertIn("<svg", html)
        self.assertIn("山梨クマ目撃マップ", html)
        self.assertIn('class="app-header__title"', html)

    def test_title_stays_a_single_h1(self):
        """見出しは1つだけにする。スクリーンリーダーの読み上げが崩れないように。"""

        html = header_brand_html("山梨クマ目撃マップ")

        self.assertEqual(1, html.count("<h1"))
        self.assertEqual(1, html.count("</h1>"))

    def test_meta_shows_the_updated_date(self):
        self.assertIn("2026年8月5日 更新", header_meta_html("2026年8月5日"))

    def test_header_title_is_22px(self):
        self.assertIn(".app-header__title", PAGE_STYLES)
        self.assertIn("font-size: 22px !important;", PAGE_STYLES)

    def test_paw_uses_the_brand_color(self):
        """足跡の色はトークンから取る。直接の色指定を残さない。"""

        self.assertIn("fill: var(--brand);", PAGE_STYLES)
        self.assertNotIn("fill=", PAW_SVG)


class SummaryTest(unittest.TestCase):
    def test_count_and_period_are_shown(self):
        html = summary_html(156, ("2026年4月2日", "2026年8月5日"))

        self.assertIn(">156<", html)
        self.assertIn("2026年4月2日 〜 2026年8月5日", html)
        self.assertIn("地図に表示中", html)

    def test_period_line_is_omitted_when_unknown(self):
        html = summary_html(0, None)

        self.assertNotIn("summary__period", html)
        self.assertIn(">0<", html)

    def test_selected_period_is_shown_with_the_count(self):
        """どの条件での件数かが数字だけでは分からないため、期間を添える。"""

        html = summary_html(48, ("2026年4月2日", "2026年8月5日"), "直近30日")

        self.assertIn("直近30日", html)
        self.assertIn("summary__scope", html)

    def test_scope_line_is_omitted_when_not_given(self):
        self.assertNotIn("summary__scope", summary_html(1, None))

    def test_scope_label_is_escaped(self):
        html = summary_html(1, None, "<script>")

        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_only_the_number_is_large(self):
        """数字だけを大きくする。単位や期間は控えめにする。"""

        self.assertIn(".summary__count {\n  font-size: 32px;", PAGE_STYLES)
        self.assertIn(".summary__unit {\n  font-size: 15px;", PAGE_STYLES)


class NoteTest(unittest.TestCase):
    def test_note_has_no_warning_colour(self):
        """座標なしの案内は警告ではない。黄色や赤で主張させない。"""

        blocks = [block.split("}")[0] for block in PAGE_STYLES.split(".note {")[1:]]
        note_css = "\n".join(blocks)

        self.assertIn("var(--text-secondary)", note_css)
        self.assertNotIn("#FF", note_css.upper())
        self.assertNotIn("YELLOW", note_css.upper())
        self.assertNotIn("RED", note_css.upper())

    def test_note_wraps_the_given_text(self):
        self.assertIn("4件は地図に出していません", note_html("4件は地図に出していません"))


class ResponsiveTest(unittest.TestCase):
    def test_breakpoints_follow_the_spec(self):
        """指示書§17。1024以上がデスクトップ、768〜1023がタブレット、767以下がスマホ。"""

        self.assertEqual(1023, BREAKPOINT_TABLET)
        self.assertEqual(767, BREAKPOINT_MOBILE)

    def test_tablet_narrows_the_sidebar(self):
        self.assertIn(f"@media (max-width: {BREAKPOINT_TABLET}px)", PAGE_STYLES)
        self.assertEqual("260px", SIDEBAR_WIDTH_TABLET)
        self.assertLess(
            int(SIDEBAR_WIDTH_TABLET.rstrip("px")), int(SIDEBAR_WIDTH.rstrip("px"))
        )

    def test_mobile_reduces_padding_and_title(self):
        mobile = PAGE_STYLES.split(f"@media (max-width: {BREAKPOINT_MOBILE}px)")[1]

        self.assertIn("padding-left: var(--space-3)", mobile)
        self.assertIn("font-size: 19px !important;", mobile)

    def test_overflow_is_fixed_at_the_cause_not_hidden(self):
        """`overflow-x: hidden`で隠すと、はみ出した中身が読めなくなる。原因側を直す。"""

        self.assertNotIn("overflow-x: hidden", PAGE_STYLES)
        self.assertIn("min-width: 0;", PAGE_STYLES)
        self.assertIn("overflow-wrap: anywhere;", PAGE_STYLES)

    def test_map_never_exceeds_its_column(self):
        self.assertIn("max-width: 100%;", PAGE_STYLES)

    def test_map_height_is_a_fixed_pixel_value(self):
        """`st_folium`はピクセルでしか高さを指定できない。viewport全高にはできない。"""

        self.assertIsInstance(MAP_HEIGHT, int)
        self.assertGreater(MAP_HEIGHT, 500)


class LegendTest(unittest.TestCase):
    def setUp(self):
        from data_utils import tone_ranges

        self.rows = [(tone, label, 3) for tone, label in tone_ranges()]
        self.html = legend_html(self.rows)

    def test_every_tone_is_listed(self):
        for tone in TONE_COLORS:
            with self.subTest(tone=tone):
                self.assertIn(TONE_COLORS[tone], self.html)

    def test_colour_is_never_the_only_signal(self):
        """指示書§18の必須項目。丸の横に必ず言葉と件数を出す。"""

        for _, label, _ in self.rows:
            self.assertIn(label, self.html)
        self.assertIn("legend__count", self.html)

    def test_legend_says_it_is_not_a_danger_level(self):
        """色を危険度と読み違えられないようにする。"""

        self.assertIn("危険度ではありません", self.html)
        self.assertIn("経過", self.html)

    def test_labels_are_escaped(self):
        html = legend_html([("recent", "<script>", 1)])

        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


class TapTargetTest(unittest.TestCase):
    def test_select_box_is_at_least_44px(self):
        """指示書§18のとおり、タップ領域は44px以上にする。"""

        self.assertIn("min-height: 44px;", PAGE_STYLES)


if __name__ == "__main__":
    unittest.main()
