"""供应商报告运行隔离测试。"""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vendor_guard.report_metadata import archive_existing_report


class ReportLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.project_root = Path(self.temp_dir.name)
        self.report_path = (
            self.project_root / "reports" / "ACME" / "onboarding-report.md"
        )
        self.report_path.parent.mkdir(parents=True)

    def test_archives_existing_report_before_new_run(self) -> None:
        self.report_path.write_text(
            "# 旧报告\n\n## 人工审批记录\n\n拒绝执行提交\n",
            encoding="utf-8",
        )

        archived_path = archive_existing_report(
            self.project_root,
            self.report_path,
            datetime(2026, 7, 23, 18, 30, tzinfo=timezone.utc),
        )

        self.assertIsNotNone(archived_path)
        assert archived_path is not None
        self.assertFalse(self.report_path.exists())
        self.assertTrue(archived_path.is_file())
        self.assertEqual(
            archived_path.parent,
            self.project_root / "report-history" / "ACME",
        )
        self.assertIn(
            "拒绝执行提交",
            archived_path.read_text(encoding="utf-8"),
        )

    def test_returns_none_when_no_previous_report_exists(self) -> None:
        archived_path = archive_existing_report(
            self.project_root,
            self.report_path,
            datetime(2026, 7, 23, 18, 30, tzinfo=timezone.utc),
        )

        self.assertIsNone(archived_path)


if __name__ == "__main__":
    unittest.main()
