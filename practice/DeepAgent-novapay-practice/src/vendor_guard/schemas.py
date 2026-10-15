"""可复用的供应商准入业务数据结构。

当前主流程主要让 Agent 写 Markdown 报告，这些 Pydantic 模型用于约束工具、
接口或后续结构化输出的稳定字段。把风险等级集中成枚举，可以避免业务代码中
出现 ``med``、``moderate`` 等无法统一比较的自由文本。
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    """风险等级；UNKNOWN 表示证据不足，不代表风险为零。

    【Python 基础】StrEnum = “成员本身就是字符串”的枚举：
    RiskLevel.LOW == "low" 为 True，可直接当字符串用（拼接、存 JSON）。
    对比裸字符串的好处和 Java enum 相同——拼错 "meduim" 会在定义处暴露，
    而不是散落在业务代码里悄悄比较失败。用 RiskLevel.LOW，不要手写 "low"。
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class RiskFinding(BaseModel):
    """单条可追溯风险发现。

    evidence 保存可回溯来源，confidence 表示结论可信程度。风险严重度和证据
    可信度是两个维度，例如“高风险、低置信度”仍是有效组合。
    """

    domain: str = Field(description="风险领域")
    title: str = Field(description="风险标题")
    level: RiskLevel
    evidence: list[str] = Field(description="证据文件路径或外部来源")
    impact: str
    recommendation: str
    # Pydantic 在模型边界强制置信度落在 [0, 1]，避免下游再做防御性判断。
    # 【Python 基础】Pydantic 的 BaseModel 和 dataclass 类似（声明字段即得构造），
    # 但多了“构造时自动校验”：传 confidence=1.5 会当场抛 ValidationError。
    # ge/le = greater/less than or equal，相当于 Java Bean Validation 的
    # @DecimalMin("0") @DecimalMax("1")。
    confidence: float = Field(ge=0, le=1)


class OnboardingDecision(BaseModel):
    """准备提交给外部采购系统的准入决定。"""

    vendor_name: str
    decision: str = Field(description="approve、conditional 或 reject")
    report_path: str
