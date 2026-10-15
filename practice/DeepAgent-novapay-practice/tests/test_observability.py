"""LangSmith 运行配置测试。"""

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from vendor_guard.observability import (
    build_langsmith_client,
    build_run_config,
    get_latest_trace_url,
    langsmith_status,
    langsmith_trace_scope,
)
from vendor_guard.settings import Settings


class ObservabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            project_root=Path("."),
            model_name="openai:test-model",
            organization_id="course-org",
            assistant_id="vendor-guard",
            environment="test",
            langsmith_tracing=True,
            langsmith_api_key="secret-value",
            langsmith_project="vendor-guard-test",
        )

    def test_run_config_contains_business_metadata(self) -> None:
        config = build_run_config(
            self.settings,
            "acme",
            "vendor-acme-001",
            run_kind="evaluation",
        )

        self.assertEqual(config["run_name"], "vendor-guard-evaluation")
        self.assertEqual(config["configurable"]["thread_id"], "vendor-acme-001")
        self.assertEqual(config["metadata"]["vendor"], "ACME")
        self.assertIn("vendor:ACME", config["tags"])
        self.assertIn("environment:test", config["tags"])

    def test_status_does_not_expose_api_key(self) -> None:
        status = langsmith_status(self.settings)

        self.assertIn("vendor-guard-test", status)
        self.assertNotIn("secret-value", status)

    @patch("vendor_guard.observability.Client")
    def test_langsmith_client_receives_key_from_settings(self, client_class) -> None:
        build_langsmith_client(self.settings)

        client_class.assert_called_once_with(
            api_key="secret-value",
            api_url=None,
            workspace_id=None,
            hide_inputs=False,
            hide_outputs=False,
        )

    @patch("vendor_guard.observability.tracing_context")
    @patch("vendor_guard.observability.build_langsmith_client")
    def test_trace_scope_binds_and_flushes_client(
        self,
        build_client,
        tracing_context,
    ) -> None:
        client = build_client.return_value

        with langsmith_trace_scope(self.settings) as bound_client:
            self.assertIs(bound_client, client)

        tracing_context.assert_called_once_with(
            enabled=True,
            project_name="vendor-guard-test",
            client=client,
        )
        client.flush.assert_called_once_with()
        client.close.assert_called_once_with()

    @patch("vendor_guard.observability.build_langsmith_client")
    def test_latest_trace_url_matches_thread(self, build_client) -> None:
        client = build_client.return_value
        matching_run = SimpleNamespace(
            name="vendor-guard-interactive",
            start_time=datetime(2026, 7, 21, tzinfo=timezone.utc),
            extra={"metadata": {"thread_id": "vendor-acme-001"}},
        )
        other_run = SimpleNamespace(
            name="vendor-guard-interactive",
            start_time=datetime(2026, 7, 20, tzinfo=timezone.utc),
            extra={"metadata": {"thread_id": "vendor-other-001"}},
        )
        client.list_runs.return_value = [other_run, matching_run]
        client.get_run_url.return_value = "https://smith.example/run/acme"

        url = get_latest_trace_url(
            self.settings,
            "vendor-acme-001",
            client=client,
        )

        self.assertEqual(url, "https://smith.example/run/acme")
        client.get_run_url.assert_called_once_with(
            run=matching_run,
            project_name="vendor-guard-test",
        )
        client.close.assert_not_called()

    @patch("vendor_guard.observability.build_langsmith_client")
    def test_latest_trace_url_is_disabled_without_tracing(self, build_client) -> None:
        settings = Settings(project_root=Path("."), langsmith_tracing=False)

        self.assertIsNone(get_latest_trace_url(settings, "vendor-acme-001"))
        build_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
