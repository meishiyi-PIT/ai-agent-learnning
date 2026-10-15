"""VendorGuard 命令行入口测试。"""

from __future__ import annotations

import unittest

from vendor_guard.cli import (
    _approval_outcome_message,
    _build_utf8_reexec_command,
    _read_approval_decision,
    _run_utf8_child,
    _should_reexec_utf8,
)


class CliTests(unittest.TestCase):
    def test_windows_without_utf8_mode_requires_reexec(self) -> None:
        self.assertTrue(_should_reexec_utf8("nt", 0))
        self.assertFalse(_should_reexec_utf8("nt", 1))
        self.assertFalse(_should_reexec_utf8("posix", 0))

    def test_reexec_command_enables_utf8_and_preserves_arguments(self) -> None:
        command = _build_utf8_reexec_command(["ACME"])

        self.assertEqual(command[1:5], ["-X", "utf8", "-m", "vendor_guard.cli"])
        self.assertEqual(command[5:], ["ACME"])

    def test_parent_utf8_wrapper_converts_ctrl_c_to_exit_130(self) -> None:
        def interrupted_runner(*_args, **_kwargs):
            raise KeyboardInterrupt

        exit_code = _run_utf8_child(
            ["ACME"],
            {"PYTHONUTF8": "1"},
            runner=interrupted_runner,
        )

        self.assertEqual(exit_code, 130)

    def test_rejected_approval_is_reported_as_completed(self) -> None:
        message = _approval_outcome_message(
            vendor_name="ACME",
            proposed_decision="conditional",
            approved=False,
            report_path="reports/ACME/onboarding-report.md",
        )

        self.assertIn("人工审批已完成", message)
        self.assertIn("未批准执行", message)
        self.assertIn("准入建议未提交", message)
        self.assertNotIn("如需提交", message)
        self.assertNotIn("等待", message)

    def test_approved_approval_is_reported_as_executed(self) -> None:
        message = _approval_outcome_message(
            vendor_name="ACME",
            proposed_decision="conditional",
            approved=True,
            report_path="reports/ACME/onboarding-report.md",
        )

        self.assertIn("人工审批已完成", message)
        self.assertIn("已批准执行", message)
        self.assertIn("提交工具已执行", message)

    def test_ctrl_c_cancels_approval_without_treating_it_as_reject(self) -> None:
        def interrupted_input(_prompt: str) -> str:
            raise KeyboardInterrupt

        self.assertEqual(
            _read_approval_decision(interrupted_input),
            "cancel",
        )

    def test_eof_cancels_approval_without_treating_it_as_reject(self) -> None:
        def closed_input(_prompt: str) -> str:
            raise EOFError

        self.assertEqual(
            _read_approval_decision(closed_input),
            "cancel",
        )


if __name__ == "__main__":
    unittest.main()
