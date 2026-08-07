"""「この地図について」の中身を確かめる。

書いてあることと実際が食い違わないようにする。
集めていないものを「集めている」と書かない。逆も書かない。
"""

import unittest
from pathlib import Path

from ui_styles import (
    CONTACT_UNSET_TEXT,
    DISCLAIMER_ITEMS,
    EXTERNAL_HOSTS,
    contact_markdown,
    disclaimer_markdown,
    privacy_markdown,
)


ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"


class PrivacyTest(unittest.TestCase):
    def setUp(self):
        self.text = privacy_markdown()

    def test_it_says_what_is_not_collected(self):
        self.assertIn("集めていません", self.text)
        self.assertIn("ログインもありません", self.text)

    def test_it_says_there_is_no_analytics(self):
        self.assertIn("アクセス解析は入れていません", self.text)

    def test_every_external_host_is_named(self):
        """「外部へ送信します」だけでは足りない。相手を名前で書く。"""

        for host, purpose in EXTERNAL_HOSTS:
            with self.subTest(host=host):
                self.assertIn(host, self.text)
                self.assertIn(purpose, self.text)

    def test_it_says_what_reaches_them(self):
        self.assertIn("IPアドレス", self.text)

    def test_it_mentions_the_hosting_provider_logs(self):
        self.assertIn("接続の記録", self.text)

    def test_it_does_not_claim_nothing_leaves_the_browser(self):
        """「外部に送信していません」と書かない。実際は送信している。"""

        self.assertNotIn("外部に送信していません", self.text)
        self.assertNotIn("外部への送信はありません", self.text)


class ContactTest(unittest.TestCase):
    def test_an_unset_contact_says_so(self):
        text = contact_markdown("")

        self.assertIn(CONTACT_UNSET_TEXT, text)
        self.assertNotIn("https://", text)

    def test_a_set_contact_is_shown(self):
        text = contact_markdown("https://github.com/example/bear-map/issues")

        self.assertIn("https://github.com/example/bear-map/issues", text)
        self.assertNotIn(CONTACT_UNSET_TEXT, text)

    def test_it_points_to_the_prefecture_for_the_data_itself(self):
        """元データの誤りは県でないと直せない。案内先を分けておく。"""

        self.assertIn("自然共生推進課", contact_markdown(""))


class DisclaimerSectionTest(unittest.TestCase):
    def setUp(self):
        self.text = disclaimer_markdown(DISCLAIMER_ITEMS)

    def test_it_repeats_the_points_shown_on_the_page(self):
        for item in DISCLAIMER_ITEMS:
            with self.subTest(item=item[:20]):
                self.assertIn(item, self.text)

    def test_it_says_the_prefecture_did_not_make_this(self):
        self.assertIn("山梨県が作成したものではありません", self.text)

    def test_it_repeats_the_prefectures_own_disclaimer(self):
        self.assertIn("完全性や正確性を保証していません", self.text)


class AboutTextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = APP.read_text(encoding="utf-8")

    def test_all_sections_are_composed(self):
        for builder in ("disclaimer_markdown(", "privacy_markdown(", "contact_markdown("):
            with self.subTest(builder=builder):
                self.assertIn(builder, self.source)

    def test_the_contact_url_can_be_set_in_one_place(self):
        self.assertIn('CONTACT_URL = ""', self.source)

    def test_it_no_longer_claims_there_is_no_auto_update(self):
        """毎日の更新を用意したので、この記述は実態と違う。"""

        self.assertNotIn("自動更新はしません", self.source)


if __name__ == "__main__":
    unittest.main()
