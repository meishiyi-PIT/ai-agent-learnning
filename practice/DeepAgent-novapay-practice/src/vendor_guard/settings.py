"""VendorGuard 配置加载与校验。

所有外部配置统一收敛到不可变 Settings 对象，业务模块不直接散落读取
``os.environ``。这种方式便于单元测试传入内存字典，也能避免模型密钥在对象
repr、日志或异常信息中意外泄露。
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


# 环境变量没有原生布尔类型，集中维护真值集合可以避免不同模块各自解释。
# 未出现在集合中的非空值按 False 处理，例如 "0"、"false" 和 "off"。
TRUE_VALUES = {"1", "true", "yes", "on"}


class ConfigurationError(ValueError):
    """配置缺失或无效。"""


def _as_bool(value: str | None, *, default: bool = False) -> bool:
    """把常见环境变量字符串转换为布尔值。"""
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


def _clean_secret(value: str | None) -> str | None:
    """规范化密钥，并把文档占位符视为未配置。"""
    if value is None:
        return None
    normalized = value.strip()
    # 示例 .env 中常保留占位符；把它们视为“未配置”，比带着假密钥请求接口
    # 后再得到难懂的鉴权错误更容易定位问题。
    if not normalized or normalized.lower() in {"replace-me", "your-api-key"}:
        return None
    return normalized


@dataclass(frozen=True)
class Settings:
    """VendorGuard 运行配置。

    frozen=True 防止运行中途被某个组件原地修改。离线评估需要切换临时
    project_root 时使用 dataclasses.replace() 创建新实例，而不是污染全局配置。
    """

    # project_root 是虚拟文件系统、Fixture、报告和 Skill 的共同物理根目录。
    project_root: Path
    model_name: str = "deepseek-v4-flash"
    # repr=False 防止调试打印整个 Settings 时把密钥带进日志或 Trace。
    model_api_key: str | None = field(default=None, repr=False)
    model_base_url: str = "https://api.deepseek.com"
    model_thinking: bool = True
    # organization_id + assistant_id 组成长期 Store 的命名空间。真实多租户部署
    # 中应替换为经过认证的租户和助手标识，不能直接信任用户输入。
    organization_id: str = "demo-org"
    assistant_id: str = "vendor-guard"
    environment: str = "local"
    langsmith_tracing: bool = False
    langsmith_api_key: str | None = field(default=None, repr=False)
    langsmith_project: str = "vendor-guard-course"
    langsmith_dataset: str = "vendor-guard-onboarding-v1"
    langsmith_workspace_id: str | None = None
    langsmith_endpoint: str | None = None
    # hide_inputs/hide_outputs 控制发送到 LangSmith 的内容，不影响本地 Agent
    # 是否能读取输入和产出报告。
    langsmith_hide_inputs: bool = False
    langsmith_hide_outputs: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        """从项目根目录的 .env 加载配置。

        load_dotenv 默认不覆盖进程中已经存在的同名环境变量，因此 CI、容器或
        临时命令行注入的配置优先级高于本地 .env。
        """
        # 当前文件位于 <project>/src/vendor_guard/，向上两级才是项目根目录。
        project_root = Path(__file__).resolve().parents[2]
        load_dotenv(project_root / ".env")
        return cls.from_mapping(os.environ, project_root=project_root)

    @classmethod
    def from_mapping(
        cls,
        values: Mapping[str, str],
        *,
        project_root: Path,
    ) -> "Settings":
        """从键值配置构造 Settings，便于测试且不依赖真实密钥。

        该方法也是唯一的字段映射入口。新增环境变量时应在这里完成默认值、
        类型转换和空值处理，避免 Settings 的不同构造路径产生不一致。
        """
        return cls(
            project_root=project_root,
            model_name=values.get("DEEPSEEK_MODEL_NAME", "deepseek-v4-flash"),
            model_api_key=_clean_secret(values.get("DEEPSEEK_API_KEY")),
            model_base_url=values.get(
                "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
            ),
            model_thinking=_as_bool(
                values.get("DEEPSEEK_ANSWER_THINKING"), default=True
            ),
            organization_id=values.get("ORGANIZATION_ID", "demo-org"),
            assistant_id=values.get("ASSISTANT_ID", "vendor-guard"),
            environment=values.get("APP_ENV", "local"),
            langsmith_tracing=_as_bool(values.get("LANGSMITH_TRACING")),
            langsmith_api_key=_clean_secret(values.get("LANGSMITH_API_KEY")),
            langsmith_project=values.get(
                "LANGSMITH_PROJECT", "vendor-guard-course"
            ),
            langsmith_dataset=values.get(
                "LANGSMITH_DATASET", "vendor-guard-onboarding-v1"
            ),
            langsmith_workspace_id=values.get("LANGSMITH_WORKSPACE_ID") or None,
            langsmith_endpoint=values.get("LANGSMITH_ENDPOINT") or None,
            langsmith_hide_inputs=_as_bool(values.get("LANGSMITH_HIDE_INPUTS")),
            langsmith_hide_outputs=_as_bool(values.get("LANGSMITH_HIDE_OUTPUTS")),
        )

    def require_model_api_key(self) -> str:
        """返回模型密钥；缺失时在发起网络请求前给出明确错误。"""
        if not self.model_api_key:
            raise ConfigurationError(
                "缺少 DEEPSEEK_API_KEY，请在项目根目录的 .env 中配置。"
            )
        return self.model_api_key

    def require_langsmith_api_key(self) -> str:
        """返回 LangSmith 密钥；缺失时在创建 Client 前给出明确错误。"""
        if not self.langsmith_api_key:
            raise ConfigurationError(
                "缺少 LANGSMITH_API_KEY，请在项目根目录的 .env 中配置。"
            )
        return self.langsmith_api_key
