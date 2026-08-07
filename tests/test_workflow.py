"""毎日の更新を行うワークフローの中身を確かめる。

YAMLとして正しいかは、GitHubへ置いて実行するまで確定しない。
ここで見るのは「意図した設定が書かれているか」まで。
書き換えたときに、決めたことが崩れていないかの番人として使う。
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "update-data.yml"


class WorkflowFileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.lines = cls.text.splitlines()

    def test_the_file_is_in_the_place_github_looks(self):
        self.assertTrue(WORKFLOW.is_file())

    def test_it_runs_once_a_day(self):
        self.assertIn("schedule:", self.text)
        self.assertIn('- cron: "0 21 * * *"', self.text)

    def test_the_schedule_is_written_in_utc_for_a_japanese_morning(self):
        """cronはUTC。21:00 UTCが翌日6:00 JST。"""

        found = re.search(r'- cron: "(\d+) (\d+) ', self.text)

        self.assertIsNotNone(found)
        minute, hour = int(found.group(1)), int(found.group(2))
        japan_hour = (hour + 9) % 24

        self.assertEqual(0, minute)
        self.assertTrue(5 <= japan_hour <= 9, f"日本時間{japan_hour}時になっている")

    def test_it_can_also_be_started_by_hand(self):
        """60日動きがないと定期実行が止まる。再開に手動実行が要る。"""

        self.assertIn("workflow_dispatch:", self.text)

    def test_it_may_write_to_the_repository(self):
        self.assertIn("permissions:", self.text)
        self.assertIn("contents: write", self.text)

    def test_it_does_not_run_twice_at_once(self):
        self.assertIn("concurrency:", self.text)

    def test_the_clock_is_japanese(self):
        """runnerの既定はUTC。日本時間の朝に動かすと前日の日付が記録される。"""

        self.assertIn("TZ: Asia/Tokyo", self.text)

    def test_it_uses_the_fetch_script(self):
        self.assertIn("python scripts/fetch_data.py", self.text)

    def test_it_runs_the_tests_before_committing(self):
        """おかしなデータをそのまま画面へ出さないため、順番が大事。"""

        fetch = self.text.index("python scripts/fetch_data.py")
        tests = self.text.index("python -m unittest discover -s tests")
        commit = self.text.index("git commit")

        self.assertLess(fetch, tests)
        self.assertLess(tests, commit)

    def test_it_commits_only_when_something_changed(self):
        self.assertIn("git diff --cached --quiet", self.text)
        self.assertIn("exit 0", self.text)

    def test_it_stages_only_the_data_folder(self):
        """取得と関係ないファイルを巻き込んでコミットしない。"""

        self.assertIn("git add data", self.text)
        self.assertNotIn("git add -A", self.text)
        self.assertNotIn("git add .", self.text)

    def test_the_actions_are_pinned_to_a_major_version(self):
        used = re.findall(r"uses: ([\w\-/]+)@(\S+)", self.text)

        self.assertEqual(
            [("actions/checkout", "v4"), ("actions/setup-python", "v5")], used
        )

    def test_no_secret_is_written_in_the_file(self):
        """トークンやパスワードをファイルへ書かない。"""

        for word in ("ghp_", "password", "api_key", "secret:"):
            with self.subTest(word=word):
                self.assertNotIn(word, self.text.lower())

    def test_indentation_uses_spaces_only(self):
        """YAMLはタブを受け付けない。"""

        for number, line in enumerate(self.lines, 1):
            with self.subTest(line=number):
                self.assertNotIn("\t", line)


if __name__ == "__main__":
    unittest.main()
