"""LangChain Tools（工具）适配层。

这里把普通 Repository 方法包装成带名称、描述和参数 Schema 的 LangChain
Tool。模型看到的是工具契约，不直接接触文件路径或 JSON 解析细节。
"""

from __future__ import annotations

from langchain.tools import tool

from vendor_guard.repository import JsonRepository
from vendor_guard.settings import Settings


# 查询工具统一读取本地 Fixture，因此结果可重复、不会访问生产系统。
# Repository 在模块导入时创建一次，后续每次工具调用只负责读取对应 JSON。
_settings = Settings.from_env()
_repository = JsonRepository(_settings.project_root / "fixtures")


@tool
def query_vendor_registry(vendor_name: str) -> dict:
    """查询供应商主数据、付款状态、履约率和历史争议。

    该 docstring 会成为模型可见的工具描述，因此应使用业务语言说明何时调用，
    不应加入模型不需要的内部实现细节。
    """
    return _repository.get_vendor(vendor_name)


@tool
def search_sanctions(vendor_name: str) -> dict:
    """查询供应商及其受益所有人的制裁或监管名单命中。"""
    return {
        "vendor": vendor_name,
        "hits": _repository.get_sanctions(vendor_name),
    }


@tool
def lookup_security_incidents(vendor_name: str) -> dict:
    """查询供应商公开披露的数据泄露和重大安全事故。"""
    return {
        "vendor": vendor_name,
        "incidents": _repository.get_incidents(vendor_name),
    }


@tool
def search_adverse_news(vendor_name: str) -> dict:
    """查询供应商近两年的重大负面新闻及来源。"""
    return {
        "vendor": vendor_name,
        "items": _repository.get_adverse_news(vendor_name),
    }


@tool
def submit_onboarding_decision(
    vendor_name: str,
    decision: str,
    report_path: str,
) -> str:
    """向采购系统提交供应商准入决定；该操作具有外部副作用。

    示例项目只返回确认字符串，但仍按真实外部写操作处理：该工具只挂载在主管
    Agent 上，并由 interrupt_on 在执行前暂停。将来替换为采购 API 时，HITL
    边界无需跟着重写。
    """
    return f"已提交：{vendor_name} -> {decision}；依据：{report_path}"
