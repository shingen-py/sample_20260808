"""色や操作のしやすさを確かめる。

指示書§18の必須項目を、目で見なくても分かる形で押さえておく。
コントラスト比はWCAGの式で計算する。
"""

import re
import unittest
from pathlib import Path

from ui_styles import (
    COLORS,
    LIST_CLASS,
    MAP_STYLES,
    PAGE_STYLES,
    TONE_COLORS,
    sighting_list_html,
)


ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".streamlit" / "config.toml"


WHITE = "#FFFFFF"

# WCAGの基準
TEXT_MIN = 4.5  # 本文の文字
GRAPHIC_MIN = 3.0  # 図形と操作部品の境界


def _channel(value: float) -> float:
    value /= 255
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    red, green, blue = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))

    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def contrast_ratio(fore: str, back: str) -> float:
    first, second = luminance(fore), luminance(back)

    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


class ContrastTest(unittest.TestCase):
    def test_the_formula_matches_known_values(self):
        """計算式そのものが正しいかを、答えの分かる組み合わせで確かめる。"""

        self.assertAlmostEqual(21.0, contrast_ratio("#000000", "#FFFFFF"), places=2)
        self.assertAlmostEqual(1.0, contrast_ratio("#777777", "#777777"), places=2)

    def test_body_text_is_readable(self):
        pairs = [
            ("text-primary", "bg"),
            ("text-primary", "surface"),
            ("text-secondary", "surface"),
            ("text-secondary", "bg"),
            ("text-secondary", "surface-muted"),
            ("brand", "surface"),
            ("brand", "bg"),
        ]

        for fore, back in pairs:
            with self.subTest(fore=fore, back=back):
                self.assertGreaterEqual(
                    contrast_ratio(COLORS[fore], COLORS[back]), TEXT_MIN
                )

    def test_cluster_number_is_readable(self):
        """クラスタは白抜きの数字。背景はブランド色。"""

        self.assertGreaterEqual(contrast_ratio(WHITE, COLORS["brand"]), TEXT_MIN)

    def test_every_pin_colour_stands_out_from_the_map(self):
        for tone, color in TONE_COLORS.items():
            with self.subTest(tone=tone):
                self.assertGreaterEqual(
                    contrast_ratio(color, COLORS["bg"]), GRAPHIC_MIN
                )

    def test_the_paw_inside_every_pin_is_visible(self):
        """足跡は白。ピンの色が明るすぎると見えなくなる。"""

        for tone, color in TONE_COLORS.items():
            with self.subTest(tone=tone):
                self.assertGreaterEqual(contrast_ratio(WHITE, color), GRAPHIC_MIN)

    def test_control_borders_are_visible(self):
        """入力欄の枠は操作部品の境界。区切り線用の`--border`とは別にする。"""

        self.assertGreaterEqual(
            contrast_ratio(COLORS["border-strong"], COLORS["surface"]), GRAPHIC_MIN
        )
        self.assertIn("border-color: var(--border-strong);", PAGE_STYLES)


class TapTargetTest(unittest.TestCase):
    def test_every_sidebar_control_is_44px(self):
        controls = {
            "市町村のプルダウン": '[data-baseweb="select"] > div',
            "期間のラジオ": '[role="radiogroup"] label',
            "絞り込みを解除ボタン": '[data-testid="stBaseButton-secondary"]',
        }

        for name, selector in controls.items():
            block = PAGE_STYLES.split(selector)[1].split("{")[1].split("}")[0]

            with self.subTest(control=name):
                self.assertIn("min-height: 44px;", block)

    def test_map_buttons_are_44px(self):
        self.assertIn("width: 44px;", MAP_STYLES)
        self.assertIn("height: 44px;", MAP_STYLES)

    def test_popup_close_button_is_44px(self):
        self.assertIn("width: 44px !important;", MAP_STYLES)


class ThemeTest(unittest.TestCase):
    """配色は明るい背景を前提にしている。テーマを固定しないと文字が読めなくなる。"""

    def setUp(self):
        self.config = CONFIG.read_text(encoding="utf-8")

    def test_config_file_exists(self):
        self.assertTrue(CONFIG.is_file())

    def test_theme_is_locked_to_light(self):
        """暗いテーマだと、暗い背景に暗い文字が乗って読めなくなる。"""

        self.assertIn('base = "light"', self.config)

    def test_theme_colours_match_the_design_tokens(self):
        expected = {
            "primaryColor": COLORS["brand"],
            "backgroundColor": COLORS["bg"],
            "secondaryBackgroundColor": COLORS["surface"],
            "textColor": COLORS["text-primary"],
        }

        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertIn(f'{key} = "{value}"', self.config)

    def test_config_is_shared_not_ignored(self):
        """`.streamlit/`を丸ごと除外すると、この設定が他の人に届かない。"""

        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertIn("!.streamlit/config.toml", ignore)

    def test_sidebar_sets_its_own_background(self):
        """期間のラジオは文字色を固定している。背景も自分で決めておかないと、
        テーマが暗いときに暗い背景へ暗い文字が乗って読めなくなる。"""

        rule = re.search(
            r'\[data-testid="stSidebar"\][^{]*\{([^}]*)\}', PAGE_STYLES
        )

        self.assertIsNotNone(rule)
        self.assertIn("background: var(--surface);", rule.group(1))
        self.assertIn("color: var(--text-primary);", rule.group(1))

    def test_widgets_that_fix_text_colour_also_fix_the_background(self):
        controls = ['[data-baseweb="select"] > div', '[data-testid="stBaseButton-secondary"]']

        for selector in controls:
            block = PAGE_STYLES.split(selector)[1].split("{")[1].split("}")[0]

            with self.subTest(selector=selector):
                self.assertIn("background:", block)
                self.assertIn("color:", block)


class SightingListAccessibilityTest(unittest.TestCase):
    """地図の上に出す一覧。文字が小さいので特に確かめる。"""

    def test_list_text_is_readable(self):
        pairs = [
            ("text-primary", "surface"),   # 市町村名
            ("text-secondary", "surface"),  # 日付・場所
            ("text-secondary", "surface-muted"),  # ホバー中の行
            ("text-primary", "surface-muted"),
        ]

        for fore, back in pairs:
            with self.subTest(fore=fore, back=back):
                self.assertGreaterEqual(
                    contrast_ratio(COLORS[fore], COLORS[back]), TEXT_MIN
                )

    def test_the_row_marker_is_not_colour_only(self):
        """選んだ行は、背景色だけでなく左の線と`aria-current`でも示す。"""

        rule = MAP_STYLES.split('__row[aria-current="true"] {')[1].split("}")[0]

        self.assertIn("box-shadow: inset 3px 0 0", rule)

    def test_keyboard_focus_is_visible_in_the_list(self):
        self.assertIn(f".{LIST_CLASS}__row:focus-visible", MAP_STYLES)
        self.assertIn(f".{LIST_CLASS}__head:focus-visible", MAP_STYLES)

    def test_rows_and_heading_are_44px(self):
        for selector in (f".{LIST_CLASS}__row {{", f".{LIST_CLASS}__head {{"):
            block = MAP_STYLES.split(selector)[1].split("}")[0]

            with self.subTest(selector=selector):
                self.assertIn("min-height: 44px;", block)

    def test_rows_are_buttons_so_the_keyboard_can_reach_them(self):
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

        self.assertIn('<button type="button"', html)
        self.assertNotIn("<div class=\"sight-list__row\"", html)


class MotionAndFocusTest(unittest.TestCase):
    def test_reduced_motion_is_respected_on_both_sides(self):
        """ページ側と地図の中は別々にCSSを入れる必要がある。"""

        self.assertIn("prefers-reduced-motion: reduce", PAGE_STYLES)
        self.assertIn("prefers-reduced-motion: reduce", MAP_STYLES)

    def test_focus_is_visible_on_both_sides(self):
        self.assertIn("focus-visible", PAGE_STYLES)
        self.assertIn("focus-visible", MAP_STYLES)

    def test_focus_outline_uses_the_brand_colour(self):
        self.assertIn("outline: 2px solid var(--brand);", PAGE_STYLES)


if __name__ == "__main__":
    unittest.main()
