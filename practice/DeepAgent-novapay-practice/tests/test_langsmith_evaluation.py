"""LangSmith 离线评估隔离测试。"""

import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from vendor_guard.langsmith_evaluation import (
    _evaluate_without_sdk_console,
    _isolated_evaluation_workspace,
)


class EvaluationWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.source_root = Path(self.temp_dir.name)
        for directory in ("data-room", "policies", "skills", "fixtures"):
            path = self.source_root / directory
            path.mkdir()
            (path / "source.txt").write_text(directory, encoding="utf-8")

        old_report = (
            self.source_root
            / "reports"
            / "ACME"
            / "onboarding-report.md"
        )
        old_report.parent.mkdir(parents=True)
        old_report.write_text("旧的交互报告", encoding="utf-8")

    def test_workspace_copies_inputs_but_not_existing_reports(self) -> None:
        with _isolated_evaluation_workspace(self.source_root) as workspace:
            self.assertEqual(
                (workspace / "data-room" / "source.txt").read_text(
                    encoding="utf-8"
                ),
                "data-room",
            )
            self.assertTrue((workspace / "policies" / "source.txt").is_file())
            self.assertTrue((workspace / "skills" / "source.txt").is_file())
            self.assertTrue((workspace / "fixtures" / "source.txt").is_file())
            self.assertTrue((workspace / "reports").is_dir())
            self.assertFalse(
                (workspace / "reports" / "ACME" / "onboarding-report.md").exists()
            )

    def test_workspace_changes_do_not_touch_real_project(self) -> None:
        with _isolated_evaluation_workspace(self.source_root) as workspace:
            sandbox_policy = workspace / "policies" / "source.txt"
            sandbox_policy.write_text("被测试用例修改", encoding="utf-8")
            sandbox_report = (
                workspace / "reports" / "ACME" / "onboarding-report.md"
            )
            sandbox_report.parent.mkdir(parents=True)
            sandbox_report.write_text("新评估报告", encoding="utf-8")

        self.assertEqual(
            (self.source_root / "policies" / "source.txt").read_text(
                encoding="utf-8"
            ),
            "policies",
        )
        self.assertEqual(
            (
                self.source_root
                / "reports"
                / "ACME"
                / "onboarding-report.md"
            ).read_text(encoding="utf-8"),
            "旧的交互报告",
        )

    @patch("vendor_guard.langsmith_evaluation.evaluate")
    def test_sdk_english_output_and_progress_are_hidden(self, evaluate) -> None:
        expected_result = object()

        def noisy_evaluate(_target, **_kwargs):
            print("View the evaluation results for experiment")
            return expected_result

        evaluate.side_effect = noisy_evaluate
        visible_stdout = io.StringIO()

        with redirect_stdout(visible_stdout):
            result = _evaluate_without_sdk_console(object(), data="dataset")

        self.assertIs(result, expected_result)
        self.assertEqual(visible_stdout.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
