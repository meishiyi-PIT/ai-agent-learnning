"""VendorGuard Supervisor Agent（主管智能体）组装。

该模块只负责“把 Agent 运行时拼起来”：模型、主管 Prompt、专业子 Agent、
虚拟文件系统、权限规则、状态存储和人工审批中断都在这里汇合。具体的 CLI
交互、报告日期校正和审批审计不放在模型侧处理，而由应用层负责。
"""

from __future__ import annotations

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from vendor_guard.backends import build_backend, build_permissions
from vendor_guard.settings import Settings
from vendor_guard.subagents import build_subagents
from vendor_guard.tools import submit_onboarding_decision


# 这段 Prompt 相当于主管 Agent 的业务执行协议。它不只描述角色，还定义了
# 调查顺序、证据质量、报告格式和审批边界。能够由 Python 代码可靠维护的事实
# （例如当前日期和真实人工审批结果）仍会在 CLI 中二次校正，不能只依赖 Prompt。
SUPERVISOR_PROMPT = """
你是供应商准入总协调人。

执行协议：
1. 先用 write_todos 建立计划，盘点 /data-room/{供应商}/。
2. 将安全、法务、财务、舆情任务委派给对应专家。
3. 只接收专家摘要；需要证据时读取 /workspace/findings/。
4. 按 /policies/vendor-onboarding.md 交叉验证并评分。
5. 报告必须写入 /reports/{供应商}/onboarding-report.md。
6. 无证据不得下结论；冲突证据必须显式列出。
7. 只有报告完成后才能调用 submit_onboarding_decision。
8. 人工审批结果由 CLI 在审批完成后写入报告，不得预先声称人工已经批准。
9. 报告日期必须逐字使用用户消息提供的日期，禁止自行估算日期。
10. 风险严重度与证据状态必须分列：风险等级使用 low、medium、high、critical
    或 unknown；证据状态使用已验证、自述待验证、缺失或冲突。
11. 供应商问卷属于自述证据，不得仅因缺少独立佐证就标记 unknown；应按声明的
    控制状态评估风险等级，同时把证据状态标为“自述待验证”并降低置信度。
12. 只有现有资料完全无法判断风险事实时才能使用 unknown；存在未整改 medium
    风险或关键 unknown 时，专业域总评不得为 low。
13. 工具调用被人工 reject 表示人工审批已经完成且未批准执行，不得描述为
    “仍待审批”“如需提交审批”或要求用户再次审批。
14. 报告正文必须逐项标注证据位置，并至少引用 4 个可追溯的具体路径；路径必须
    以 /data-room/、/workspace/findings/ 或 /policies/ 开头。
"""


def build_chat_model(settings: Settings) -> ChatOpenAI:
    """使用 Settings 中的 DeepSeek 配置创建 OpenAI 兼容模型。

    DeepSeek 提供 OpenAI 兼容接口，因此这里使用 ChatOpenAI 适配器。思考模式
    不是 LangChain 的通用参数，需要通过 extra_body 原样传给模型服务。
    """
    thinking_type = "enabled" if settings.model_thinking else "disabled"
    return ChatOpenAI(
        model=settings.model_name,
        api_key=settings.require_model_api_key(),
        base_url=settings.model_base_url,
        extra_body={"thinking": {"type": thinking_type}},
    )


def build_vendor_guard(settings: Settings | None = None):
    """创建一套可执行的本地 Deep Agent 工作流。

    返回值是已经编译好的 LangGraph 风格 Agent，可通过 invoke() 启动，也可以
    在触发 interrupt 后使用同一 thread_id 恢复。当前 Store 和 Checkpointer
    都是内存实现，所以状态只在本进程生命周期内有效。
    """
    settings = settings or Settings.from_env()
    # 长期记忆按“组织 + 助手”隔离，避免多个租户或多个助手互相读到数据。
    namespace = (settings.organization_id, settings.assistant_id)
    # Store 保存跨线程记忆；Checkpointer 保存单个线程暂停、恢复所需的图状态。
    # 当前使用内存实现，进程退出后不会持久化。
    store = InMemoryStore()
    checkpointer = InMemorySaver()

    # create_deep_agent 会为主管补充任务规划、文件操作和委派等通用能力。
    # 顶层 tools 只放最终提交工具；四个查询工具分别下放给对应子 Agent，
    # 这样主管不能绕过专业角色直接调用领域工具。
    return create_deep_agent(
        model=build_chat_model(settings),
        system_prompt=SUPERVISOR_PROMPT,
        tools=[submit_onboarding_decision],
        subagents=build_subagents(),
        skills=["/skills/"],
        memory=["/memories/AGENTS.md"],
        backend=build_backend(settings.project_root, namespace),
        store=store,
        permissions=build_permissions(),
        # 提交决定属于有副作用的动作。Agent 调用工具时先暂停图，只有外部明确
        # approve/reject 后，CLI 才会恢复执行，而不是让模型自行完成审批。
        # allowed_decisions 约束的是恢复命令的类型，不代表默认批准。
        interrupt_on={
            "submit_onboarding_decision": {
                "allowed_decisions": ["approve", "reject"]
            }
        },
        checkpointer=checkpointer,
    )
