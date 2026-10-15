"""主管 Agent 执行协议测试。"""

import unittest

from vendor_guard.agent import SUPERVISOR_PROMPT


class SupervisorPromptTests(unittest.TestCase):
    def test_requires_traceable_evidence_paths_in_report(self) -> None:
        self.assertIn("至少引用 4 个", SUPERVISOR_PROMPT)
        self.assertIn("/data-room/", SUPERVISOR_PROMPT)
        self.assertIn("/workspace/findings/", SUPERVISOR_PROMPT)
        self.assertIn("/policies/", SUPERVISOR_PROMPT)


if __name__ == "__main__":
    unittest.main()
