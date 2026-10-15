# -*- coding: utf-8 -*-
"""
综合项目 · MiniAgent —— 无框架手写 Agent 工具循环   （约 5 分钟通读 + 运行）

这是 Multi-Agent/agent.py 的教学简化版：不需要 API Key，用一个"假 LLM"模拟决策，
但 Agent 循环的骨架（决策 -> 调工具 -> 把结果喂回去 -> 直到给出最终答案）和真实代码一模一样。

六课语法在本文件中的分布（标在各段注释里）：
  L01 f-string / dict / list      L02 类 / try-except / **kwargs
  L03 TypedDict / Literal / Pydantic      L04 推导式 / enumerate
  L05 装饰器注册工具      L06 async 并发（结尾附加演示）

运行方式：python mini_agent.py
"""

import asyncio
import json
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field, ValidationError

# ============================================================
# 第 1 步 · 用装饰器搭一个工具注册表（L05）
# ============================================================
TOOLS: dict[str, dict[str, Any]] = {}

def tool(func):
    """模仿 LangChain 的 @tool：登记函数，docstring 即工具说明。"""
    TOOLS[func.__name__] = {"func": func, "description": func.__doc__}
    return func

@tool
def calculator(expression: str) -> str:
    """计算数学表达式，如 '25 * 4 + 10'。"""
    try:                                            # L02: 工具内部自己兜住异常
        return str(eval(expression, {"__builtins__": {}}))   # 禁用内置函数的受限 eval
    except Exception as e:
        return f"计算失败: {e}"

@tool
def search_knowledge(query: str) -> str:
    """在本地知识库中检索。"""
    kb = {
        "langgraph": "LangGraph 是用图（节点+边）编排 LLM 工作流的框架，核心概念是 State。",
        "rag": "RAG = 检索增强生成：先检索相关文档，再把文档塞进 prompt 让 LLM 回答。",
    }
    # L04: 推导式过滤 —— 找出 query 里提到的知识条目
    hits = [text for key, text in kb.items() if key in query.lower()]
    return "\n".join(hits) if hits else "知识库中没有相关内容"

# ============================================================
# 第 2 步 · 定义 LLM 决策的数据模型（L03: Pydantic）
# ============================================================
class Decision(BaseModel):
    """LLM 每轮的决策：要么调工具，要么给最终答案。"""
    action: Literal["call_tool", "final_answer"]        # L03: Literal 限定取值
    tool_name: str | None = None                        # L03: X | None
    tool_args: dict[str, Any] = Field(default_factory=dict)
    answer: str | None = None

# ============================================================
# 第 3 步 · Agent 的状态（L03: TypedDict，和 LangGraph State 同款写法）
# ============================================================
class AgentState(TypedDict, total=False):
    query: str
    messages: list[dict]        # L01: 消息就是 dict 组成的 list
    tool_calls: int
    final_answer: str

# ============================================================
# 第 4 步 · 假 LLM：真实版这里是 client.chat.completions.create(**kwargs)
# ============================================================
def fake_llm(messages: list[dict]) -> str:
    """按简单规则返回 JSON 字符串，模拟 LLM 的决策输出。"""
    last = messages[-1]["content"]                      # L01: 下标 -1 取最后一条
    if last.startswith("工具结果"):                     # 已有工具结果 -> 给最终答案
        return json.dumps({"action": "final_answer",
                           "answer": f"根据工具结果得出：{last.removeprefix('工具结果:')}"},
                          ensure_ascii=False)
    if any(ch.isdigit() for ch in last):                # 含数字 -> 调计算器
        return json.dumps({"action": "call_tool", "tool_name": "calculator",
                           "tool_args": {"expression": "25 * 4 + 10"}})
    return json.dumps({"action": "call_tool", "tool_name": "search_knowledge",
                       "tool_args": {"query": last}})

# ============================================================
# 第 5 步 · Agent 类：核心工具循环（L02: 类；对照 Multi-Agent/agent.py）
# ============================================================
class MiniAgent:
    def __init__(self, name: str = "mini-agent", max_rounds: int = 5):
        self.name = name
        self.max_rounds = max_rounds

    def run(self, query: str) -> AgentState:
        """Agent 主循环：LLM 决策 -> 执行工具 -> 结果喂回 -> 直到 final_answer。"""
        state: AgentState = {"query": query, "messages": [], "tool_calls": 0}
        state["messages"].append({"role": "user", "content": query})

        for round_i in range(1, self.max_rounds + 1):           # L02: for + range
            raw = fake_llm(state["messages"])                   # ① 问 LLM 下一步干什么

            try:                                                # ② 校验 LLM 输出（L03）
                decision = Decision.model_validate_json(raw)
            except ValidationError as e:                        # L02: LLM 输出不可信，必须兜底
                print(f"[第{round_i}轮] LLM 输出不合法: {e.errors()[0]['msg']}")
                break

            if decision.action == "final_answer":               # ③ 拿到答案，结束循环
                state["final_answer"] = decision.answer or ""
                print(f"[第{round_i}轮] 最终答案: {decision.answer}")
                break

            # ④ 执行工具：查注册表 -> **解包参数调用（L02/L05）
            entry = TOOLS.get(decision.tool_name)               # L01: .get 防 KeyError
            if entry is None:
                result = f"未知工具: {decision.tool_name}"
            else:
                result = entry["func"](**decision.tool_args)    # L02: **dict 解包成关键字参数

            print(f"[第{round_i}轮] 调用 {decision.tool_name}({decision.tool_args}) -> {result[:50]}")
            state["tool_calls"] += 1
            # ⑤ 把工具结果作为新消息喂回给 LLM —— Agent 循环的灵魂
            state["messages"].append({"role": "tool", "content": f"工具结果:{result}"})

        return state


def print_report(state: AgentState) -> None:
    """L01/L04: f-string + enumerate 输出执行报告。"""
    print(f"\n===== 执行报告 =====")
    print(f"问题: {state['query']}")
    print(f"工具调用次数: {state.get('tool_calls', 0)}")
    for i, msg in enumerate(state.get("messages", []), 1):
        print(f"  {i}. [{msg['role']}] {msg['content'][:60]}")
    print(f"答案: {state.get('final_answer', '（无）')}")

# ============================================================
# 附加 · 异步版入口（L06）：并发跑两个 Agent 任务
# ============================================================
async def run_async(agent: MiniAgent, query: str) -> AgentState:
    """真实项目里 LLM 调用是 await client...；这里用线程把同步 run 包成协程即可演示。"""
    return await asyncio.to_thread(agent.run, query)

async def async_demo() -> None:
    agent = MiniAgent()
    print("\n===== 异步并发跑两个任务 =====")
    s1, s2 = await asyncio.gather(                      # L06: gather 并发
        run_async(agent, "帮我算 25 * 4 + 10"),
        run_async(agent, "什么是 rag？"),
    )
    # L04: 推导式汇总
    answers = [s.get("final_answer", "?") for s in (s1, s2)]
    print(f"两个任务的答案: {answers}")

# ============================================================
# 入口（L01: if __name__）
# ============================================================
if __name__ == "__main__":
    agent = MiniAgent()

    print("===== 任务1：需要计算器 =====")
    state = agent.run("帮我算 25 * 4 + 10")
    print_report(state)

    print("\n===== 任务2：需要知识库 =====")
    state = agent.run("什么是 langgraph？")
    print_report(state)

    asyncio.run(async_demo())

    print("\n[完成] 跑通了！现在去读真实版：C:/workspace/Multi-Agent/agent.py（结构一模一样，只是 LLM 是真的）")
