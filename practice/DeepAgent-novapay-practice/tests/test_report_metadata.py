"""可信报告元数据测试。"""

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from vendor_guard.report_metadata import (
    stamp_report_date,
    validate_report_risk_semantics,
)


class ReportMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.report_path = Path(self.temp_dir.name) / "report.md"

    def test_replaces_model_generated_report_date(self) -> None:
        self.report_path.write_text(
            "# ACME 报告\n\n**报告日期：2026-05-12**\n",
            encoding="utf-8",
        )

        changed = stamp_report_date(self.report_path, date(2026, 7, 23))

        self.assertTrue(changed)
        report = self.report_path.read_text(encoding="utf-8")
        self.assertIn("**报告日期：** 2026-07-23", report)
        self.assertNotIn("2026-05-12", report)

    def test_inserts_date_when_model_omits_it(self) -> None:
        self.report_path.write_text("# ACME 报告\n\n正文\n", encoding="utf-8")

        stamp_report_date(self.report_path, date(2026, 7, 23))

        report = self.report_path.read_text(encoding="utf-8")
        self.assertTrue(
            report.startswith("# ACME 报告\n\n**报告日期：** 2026-07-23")
        )

    def test_canonical_date_is_idempotent(self) -> None:
        self.report_path.write_text(
            "# ACME 报告\n\n**报告日期：** 2026-07-23\n",
            encoding="utf-8",
        )

        self.assertFalse(
            stamp_report_date(self.report_path, date(2026, 7, 23))
        )

    def test_requires_separate_evidence_status_column(self) -> None:
        self.report_path.write_text(
            "# 报告\n\n### 安全域\n\n| 风险项 | 等级 | 证据位置 |\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "证据状态"):
            validate_report_risk_semantics(self.report_path)

    def test_rejects_low_domain_with_medium_detail(self) -> None:
        self.report_path.write_text(
            "# 报告\n\n"
            "| 专业域 | 风险等级 |\n"
            "|---|---|\n"
            "| **安全 (Security)** | **LOW** |\n\n"
            "### 安全域\n\n"
            "| 风险项 | 风险等级 | 证据状态 |\n"
            "|---|---|---|\n"
            "| PT-02 | Medium | 已验证 |\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "总评为 low"):
            validate_report_risk_semantics(self.report_path)

    def test_accepts_medium_domain_with_separated_evidence_status(self) -> None:
        self.report_path.write_text(
            "# 报告\n\n"
            "| 专业域 | 风险等级 |\n"
            "|---|---|\n"
            "| **安全 (Security)** | **MEDIUM** |\n\n"
            "### 安全域\n\n"
            "| 风险项 | 风险等级 | 证据状态 |\n"
            "|---|---|---|\n"
            "| PT-02 | Medium | 已验证 |\n"
            "| MFA | Low | 自述待验证 |\n",
            encoding="utf-8",
        )

        validate_report_risk_semantics(self.report_path)

    def test_accepts_numbered_security_domain_heading(self) -> None:
        self.report_path.write_text(
            "# 报告\n\n"
            "| 专业域 | 风险等级 |\n"
            "|---|---|\n"
            "| **安全 (Security)** | **MEDIUM** |\n\n"
            "### 2.1 安全域 — 风险等级：medium\n\n"
            "| 风险项 | 风险等级 | 证据状态 |\n"
            "|---|---|---|\n"
            "| PT-02 | Medium | 已验证 |\n",
            encoding="utf-8",
        )

        validate_report_risk_semantics(self.report_path)

    def test_accepts_numbered_security_review_heading(self) -> None:
        self.report_path.write_text(
            "# UNKNOWN 报告\n\n"
            "| 专业域 | 风险等级 |\n"
            "|---|---|\n"
            "| 安全审查 | high |\n\n"
            "### 3.1 安全审查（Security Review）\n\n"
            "| 风险领域 | 风险等级 | 证据状态 |\n"
            "|---|---|---|\n"
            "| 身份与访问控制 | unknown | 缺失 |\n",
            encoding="utf-8",
        )

        validate_report_risk_semantics(self.report_path)

    def test_accepts_level_two_security_review_with_subsections(self) -> None:
        self.report_path.write_text(
            "# ACME 报告\n\n"
            "| 专业域 | 风险等级 |\n"
            "|---|---|\n"
            "| 安全审查 | medium |\n\n"
            "## 3. 安全审查（Security Review）\n\n"
            "### 3.1 总体评价\n\n"
            "风险等级：medium\n\n"
            "### 3.2 逐项风险\n\n"
            "| 风险项 | 风险等级 | 证据状态 |\n"
            "|---|---|---|\n"
            "| PT-02 | medium | 已验证 |\n\n"
            "## 4. 法务审查\n",
            encoding="utf-8",
        )

        validate_report_risk_semantics(self.report_path)


if __name__ == "__main__":
    unittest.main()
