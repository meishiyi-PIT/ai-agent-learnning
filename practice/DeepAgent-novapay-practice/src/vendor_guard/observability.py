"""VendorGuard 的 LangSmith Trace 配置与查询。

本模块不实现业务日志，而是统一一次 Agent 运行的名称、标签、元数据和 Client
生命周期。LangChain/Deep Agents 在 tracing_context 中自动记录模型、工具和
子 Agent 的父子 Run，业务 Tool 无需手工向 LangSmith 发送事件。
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from langsmith import Client, tracing_context

from vendor_guard.settings import Settings


# 【Python 基础】参数列表里单独一个 “*,” = 分界线：它后面的参数只能用
# “关键字”方式传（build_run_config(s, v, t, run_kind="evaluation")），
# 不能按位置传。Java 没有这机制；作用是防止调用处写一串裸参数时把
# 可选参数的位置传错，逼你写出参数名、代码自解释。
def build_run_config(
    settings: Settings,
    vendor: str,
    thread_id: str,
    *,
    run_kind: str = "interactive",
) -> dict[str, Any]:
    """生成 LangGraph 与 LangSmith 共用的运行配置。

    configurable.thread_id 参与状态恢复；run_name、tags 和 metadata 用于
    LangSmith 检索和实验过滤。同一字段同时服务运行时和可观测平台，可避免
    两套标识无法关联。
    """
    normalized_vendor = vendor.upper()
    return {
        # configurable.thread_id 供 LangGraph Checkpointer 定位会话状态；同一个
        # ID 也写入 metadata，便于稍后从 LangSmith 反查对应 Trace。
        "configurable": {"thread_id": thread_id},
        # interactive 与 evaluation 使用不同根运行名，查询 Trace 时不会把
        # 手动运行和离线实验混在一起。
        "run_name": f"vendor-guard-{run_kind}",
        "tags": [
            "vendor-guard",
            "workflow:onboarding",
            f"vendor:{normalized_vendor}",
            f"environment:{settings.environment}",
            f"run-kind:{run_kind}",
        ],
        "metadata": {
            "vendor": normalized_vendor,
            "thread_id": thread_id,
            "workflow": "vendor-onboarding",
            "run_kind": run_kind,
            "environment": settings.environment,
            "organization_id": settings.organization_id,
            "assistant_id": settings.assistant_id,
            "model_name": settings.model_name,
        },
    }


def langsmith_status(settings: Settings) -> str:
    """返回不泄露密钥的 LangSmith 状态文本。

    这里只报告“是否启用、配置是否完整、项目名”，不会打印 API Key、Workspace
    ID 等凭证信息。
    """
    if not settings.langsmith_tracing:
        return "LangSmith Trace：关闭（LANGSMITH_TRACING=false）"
    if not settings.langsmith_api_key:
        return "LangSmith Trace：配置不完整（缺少 LANGSMITH_API_KEY）"
    return f"LangSmith Trace：开启（项目：{settings.langsmith_project}）"


def build_langsmith_client(settings: Settings) -> Client:
    """只使用 Settings 中的凭证创建 LangSmith 客户端。

    hide_inputs/hide_outputs 在 Client 层统一生效，避免某个 Trace 调用遗漏敏感
    数据策略。endpoint 和 workspace_id 允许连接非默认区域或指定工作区。
    """
    return Client(
        api_key=settings.require_langsmith_api_key(),
        api_url=settings.langsmith_endpoint,
        workspace_id=settings.langsmith_workspace_id,
        hide_inputs=settings.langsmith_hide_inputs,
        hide_outputs=settings.langsmith_hide_outputs,
    )


# 【Python 基础】@contextmanager：把“生成器函数”变成能用 with 的上下文管理器。
# 之前在 cli.py 见过 with 的用法（≈ Java try-with-resources），这里是“怎么自己
# 造一个 with 能用的东西”：
#   · yield 之前的代码 = 进入 with 时执行（≈ 获取资源）；
#   · yield 出去的值   = 绑定给 with ... as x 的 x；
#   · yield 之后 / finally = 离开 with 时执行（≈ 释放资源，异常也保证跑）。
# 函数体在 yield 处“暂停”，等 with 块里的代码全部跑完才继续往下走。
@contextmanager
def langsmith_trace_scope(settings: Settings):
    """为一次完整交互显式绑定 Client，并在退出前上传缓存 Trace。

    Trace 关闭时提供 no-op 上下文，使 CLI 不需要维护两套控制流。开启时 yield
    Client，调用方可在人工审批前主动 flush 并查询当前 Trace URL。
    """
    if not settings.langsmith_tracing:
        yield None
        return

    client = build_langsmith_client(settings)
    try:
        with tracing_context(
            enabled=True,
            project_name=settings.langsmith_project,
            client=client,
        ):
            yield client
    finally:
        # Trace 客户端会批量异步上传；退出作用域前主动 flush，避免短命令结束时
        # 最后一批运行记录还留在本地队列。
        client.flush()
        client.close()


def get_latest_trace_url(
    settings: Settings,
    thread_id: str,
    *,
    run_name: str = "vendor-guard-interactive",
    client: Client | None = None,
) -> str | None:
    """查询指定任务线程最新一次根运行的 LangSmith URL。

    查询同时约束根运行、run_name 和 metadata.thread_id。仅按供应商名称查询
    可能命中旧运行或某个子 Agent，因此不足以作为本次人工审批的审计链接。
    """
    if not settings.langsmith_tracing:
        return None

    # 调用者传入的 Client 可能还要继续使用，只有本函数创建的实例才由本函数关闭。
    owns_client = client is None
    client = client or build_langsmith_client(settings)
    try:
        matching_runs = []
        # 只在根运行中按运行名和 thread_id 精确匹配，避免把某个子 Agent 的
        # Trace 或同一供应商的另一次运行误当成当前交互。
        for run in client.list_runs(
            project_name=settings.langsmith_project,
            is_root=True,
            limit=100,
        ):
            metadata = (run.extra or {}).get("metadata", {})
            if run.name == run_name and metadata.get("thread_id") == thread_id:
                matching_runs.append(run)

        if not matching_runs:
            return None

        # 【Python 基础】max(列表, key=函数) = “按什么比大小”：对每个元素调 key
        # 函数取比较值，返回原元素中最大的那个。这里即“取 start_time 最新的 run”。
        # ≈ Java 的 Collections.max(list, Comparator.comparing(Run::getStartTime))。
        # 和之前 next((...), None) 是姊妹句式：next 找第一个，max/min 找最值。
        latest_run = max(matching_runs, key=lambda run: run.start_time)
        return client.get_run_url(
            run=latest_run,
            project_name=settings.langsmith_project,
        )
    finally:
        if owns_client:
            client.close()
