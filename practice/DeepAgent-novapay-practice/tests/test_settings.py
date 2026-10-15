"""集中配置与密钥保护测试。"""

from pathlib import Path
import unittest

from vendor_guard.agent import build_chat_model
from vendor_guard.settings import ConfigurationError, Settings


class SettingsTests(unittest.TestCase):
    def test_all_api_keys_are_loaded_from_mapping(self) -> None:
        settings = Settings.from_mapping(
            {
                "DEEPSEEK_API_KEY": "deepseek-secret",
                "DEEPSEEK_BASE_URL": "https://api.deepseek.example",
                "DEEPSEEK_MODEL_NAME": "deepseek-test",
                "DEEPSEEK_ANSWER_THINKING": "false",
                "LANGSMITH_API_KEY": "langsmith-secret",
            },
            project_root=Path("."),
        )

        self.assertEqual(settings.require_model_api_key(), "deepseek-secret")
        self.assertEqual(settings.require_langsmith_api_key(), "langsmith-secret")
        self.assertEqual(settings.model_name, "deepseek-test")
        self.assertFalse(settings.model_thinking)

    def test_api_keys_are_hidden_from_settings_repr(self) -> None:
        settings = Settings(
            project_root=Path("."),
            model_api_key="deepseek-secret",
            langsmith_api_key="langsmith-secret",
        )

        rendered = repr(settings)
        self.assertNotIn("deepseek-secret", rendered)
        self.assertNotIn("langsmith-secret", rendered)

    def test_missing_model_key_has_clear_error(self) -> None:
        settings = Settings(project_root=Path("."))

        with self.assertRaisesRegex(ConfigurationError, "DEEPSEEK_API_KEY"):
            settings.require_model_api_key()

    def test_chat_model_uses_settings_instead_of_environment(self) -> None:
        settings = Settings(
            project_root=Path("."),
            model_name="deepseek-test",
            model_api_key="deepseek-secret",
            model_base_url="https://api.deepseek.example",
            model_thinking=False,
        )

        model = build_chat_model(settings)

        self.assertEqual(model.model_name, "deepseek-test")
        self.assertEqual(model.openai_api_base, "https://api.deepseek.example")
        self.assertNotIn("deepseek-secret", repr(model))
        self.assertEqual(
            model.extra_body,
            {"thinking": {"type": "disabled"}},
        )


if __name__ == "__main__":
    unittest.main()
