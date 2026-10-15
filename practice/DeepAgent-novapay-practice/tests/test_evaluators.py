"""确定性 LangSmith 代码评估器测试。"""

import unittest

from vendor_guard.evaluators import (
    approval_boundary,
    evidence_traceability,
    protected_sources_unchanged,
    report_completeness,
)


class EvaluatorTests(unittest.TestCase):
    def test_complete_report_gets_full_score(self) -> None:
        report = "风险、证据、unknown、冲突、整改、复审"
        result = report_completeness({"report": report})
        self.assertEqual(result["score"], 1.0)

    def test_missing_terms_reduce_report_score(self) -> None:
        result = report_completeness({"report": "风险与证据"})
        self.assertLess(result["score"], 1.0)
        self.assertIn("缺少", result["comment"])

    def test_evidence_paths_are_counted(self) -> None:
        report = (
            "/data-room/ACME/a.md /data-room/ACME/b.md "
            "/workspace/findings/security.md /policies/vendor-onboarding.md"
        )
        result = evidence_traceability({"report": report})
        self.assertEqual(result["score"], 1.0)

    def test_approval_expectation_can_be_false(self) -> None:
        result = approval_boundary(
            {"interrupted": False},
            {"expect_interrupt": False},
        )
        self.assertEqual(result["score"], 1.0)

    def test_protected_sources_must_remain_unchanged(self) -> None:
        result = protected_sources_unchanged(
            {"protected_sources_unchanged": True}
        )
        self.assertEqual(result["score"], 1.0)


if __name__ == "__main__":
    unittest.main()
