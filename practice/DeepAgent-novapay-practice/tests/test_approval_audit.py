"""人工审批审计记录测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vendor_guard.approval_audit import (
    ApprovalAuditRecord,
    append_approval_audit,
    resolve_report_path,
)


class ApprovalAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.project_root = Path(self.temp_dir.name)
        self.report_path = self.project_root / "reports" / "ACME" / "onboarding-report.md"
        self.report_path.parent.mkdir(parents=True)
        self.report_path.write_text("# ACME 报告\n", encoding="utf-8")

    def _record(self, *, human_decision: str = "approve") -> ApprovalAuditRecord:
        status = "提交工具已执行" if human_decision == "approve" else "未执行（人工拒绝）"
        return ApprovalAuditRecord(
            record_id="approval-001",
            vendor_name="ACME",
            proposed_decision="conditional",
            human_decision=human_decision,
            handled_at=datetime(
                2026,
                7,
                23,
                15,
                42,
                18,
                tzinfo=timezone(timedelta(hours=8)),
            ),
            operator="course-user",
            thread_id="vendor-acme-001",
            trace_url="https://smith.example/r/trace-id",
            execution_status=status,
        )

    def test_resolves_virtual_report_path_inside_project(self) -> None:
        resolved = resolve_report_path(
            self.project_root,
            "/reports/ACME/onboarding-report.md",
        )

        self.assertEqual(resolved, self.report_path.resolve())

    def test_rejects_path_outside_reports_directory(self) -> None:
        with self.assertRaisesRegex(ValueError, "reports"):
            resolve_report_path(self.project_root, "/reports/../.env")

    def test_approved_record_contains_audit_fields(self) -> None:
        append_approval_audit(self.report_path, self._record())

        report = self.report_path.read_text(encoding="utf-8")
        self.assertIn("## 人工审批记录", report)
        self.assertIn("| 建议准入决定 | conditional |", report)
        self.assertIn("| 人工处理结果 | 同意执行提交 |", report)
        self.assertIn("2026-07-23T15:42:18+08:00", report)
        self.assertIn("| 操作人（本机账户，未经身份认证） | course-user |", report)
        self.assertIn("https://smith.example/r/trace-id", report)
        self.assertIn("| 提交状态 | 提交工具已执行 |", report)

    def test_rejected_record_says_submission_was_not_executed(self) -> None:
        self.report_path.write_text(
            "# ACME 报告\n\n"
            "> ⏳ **本报告已提交人工审批，审批结果将由 CLI 写入。**\n",
            encoding="utf-8",
        )
        append_approval_audit(
            self.report_path,
            self._record(human_decision="reject"),
        )

        report = self.report_path.read_text(encoding="utf-8")
        self.assertIn("| 人工处理结果 | 拒绝执行提交 |", report)
        self.assertIn("| 提交状态 | 未执行（人工拒绝） |", report)
        self.assertIn("人工审批已完成：拒绝执行提交", report)
        self.assertNotIn("审批结果将", report)

    def test_same_record_is_not_appended_twice(self) -> None:
        record = self._record()

        self.assertTrue(append_approval_audit(self.report_path, record))
        self.assertFalse(append_approval_audit(self.report_path, record))

        report = self.report_path.read_text(encoding="utf-8")
        self.assertEqual(report.count("## 人工审批记录"), 1)


if __name__ == "__main__":
    unittest.main()
