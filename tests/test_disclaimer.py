"""画面に出す免責を確かめる。

安全に関わる情報を扱うため、注意書きが「開かないと読めない場所」だけに
置かれていないかを見る。
"""

import unittest
from pathlib import Path

from ui_styles import (
    DISCLAIMER_ITEMS,
    DISCLAIMER_TITLE,
    PAGE_STYLES,
    disclaimer_html,
)


ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"


class DisclaimerContentTest(unittest.TestCase):
    def setUp(self):
        self.html = disclaimer_html()

    def test_it_covers_the_four_points(self):
        """位置の精度、更新の遅れ、責任、状況欄の扱い。"""

        topics = {
            "位置の精度": "目安",
            "更新の遅れ": "公式発表",
            "責任": "責任を負いません",
            "状況欄の扱い": "特定する目的",
        }

        for name, word in topics.items():
            with self.subTest(topic=name):
                self.assertIn(word, self.html)

    def test_it_says_how_often_the_data_is_updated(self):
        self.assertIn("1日1回", self.html)

    def test_it_names_who_to_check_in_an_emergency(self):
        self.assertIn("山梨県", self.html)
        self.assertIn("市町村", self.html)

    def test_every_item_becomes_a_list_row(self):
        self.assertEqual(len(DISCLAIMER_ITEMS), self.html.count("<li>"))

    def test_the_title_is_shown(self):
        self.assertIn(DISCLAIMER_TITLE, self.html)

    def test_text_is_escaped(self):
        html = disclaimer_html(("<script>alert(1)</script>",))

        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


class DisclaimerPlacementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = APP.read_text(encoding="utf-8")

    def test_it_is_shown_without_opening_anything(self):
        """`st.popover`や`st.expander`の中ではなく、画面に直接出す。"""

        self.assertIn("st.markdown(disclaimer_html(), unsafe_allow_html=True)", self.source)

        before = self.source.index("disclaimer_html()")
        popover = self.source.index("st.popover")

        self.assertGreater(before, popover, "免責がポップオーバーより前にある")

    def test_it_sits_above_the_source_credit(self):
        """出所表示より先に免責を読ませる。"""

        self.assertLess(
            self.source.index("disclaimer_html()"),
            self.source.rindex("source_text(fetched_label)"),
        )

    def test_the_styles_exist_on_the_page_side(self):
        """免責はStreamlitのページに出す。地図の中ではない。"""

        self.assertIn(".disclaimer {", PAGE_STYLES)
        self.assertIn(".disclaimer__items li {", PAGE_STYLES)

    def test_it_does_not_use_a_warning_colour(self):
        rule = PAGE_STYLES.split(".disclaimer {")[1].split("}")[0]

        self.assertIn("var(--surface-muted)", rule)
        self.assertNotIn("red", rule.lower())
        self.assertNotIn("yellow", rule.lower())


class ZoomHintTest(unittest.TestCase):
    """U-012でズームボタンを右下へ移した。案内の文言も合っているか。"""

    def test_the_hint_points_to_the_right_place(self):
        source = APP.read_text(encoding="utf-8")

        self.assertIn("右下の + − ボタン", source)
        self.assertNotIn("左上の + − ボタン", source)


if __name__ == "__main__":
    unittest.main()
