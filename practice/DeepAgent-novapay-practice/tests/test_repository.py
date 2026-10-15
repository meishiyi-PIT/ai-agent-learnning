"""纯业务数据访问测试。"""

from pathlib import Path
import unittest

from vendor_guard.repository import JsonRepository


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class JsonRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = JsonRepository(PROJECT_ROOT / "fixtures")

    def test_vendor_lookup_is_case_insensitive(self) -> None:
        vendor = self.repository.get_vendor("acme")
        self.assertTrue(vendor["found"])
        self.assertEqual(vendor["vendor"], "ACME")

    def test_unknown_vendor_returns_not_found(self) -> None:
        vendor = self.repository.get_vendor("unknown")
        self.assertFalse(vendor["found"])

    def test_security_incident_lookup(self) -> None:
        incidents = self.repository.get_incidents("ACME")
        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0]["severity"], "medium")

    def test_sanctions_are_empty_for_acme(self) -> None:
        self.assertEqual(self.repository.get_sanctions("ACME"), [])


if __name__ == "__main__":
    unittest.main()

