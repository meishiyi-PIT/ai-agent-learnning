"""VendorGuard Deep Agents 项目的公共入口。

包根只暴露 build_vendor_guard，并通过函数内导入避免 ``import vendor_guard``
时立即加载模型 SDK、读取配置或初始化工具。这样纯业务模块和单元测试可以在
没有真实 API Key 的环境中正常导入。
"""

from __future__ import annotations

from typing import Any


def build_vendor_guard(*args: Any, **kwargs: Any):
    """延迟导入 Agent 集成层，并透明转发构造参数。"""
    from vendor_guard.agent import build_vendor_guard as _build_vendor_guard

    return _build_vendor_guard(*args, **kwargs)


__all__ = ["build_vendor_guard"]
