# -*- coding: utf-8 -*-
"""
Lesson 03 · 类型系统：TypedDict / Literal / Enum / dataclass / Pydantic   （约 12 分钟）

这是读懂 LangGraph 和结构化输出的关键一课。
对应你的课件代码：Agentic_Rag/app/state.py（TypedDict）、schemas.py（Pydantic + StrEnum）
运行方式：python lessons/03_typing_models.py
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal, TypedDict

# ============================================================
# 1. 泛型注解与联合类型 —— 现代 Python 的标准写法
# ============================================================
# list[str]        字符串列表
# dict[str, Any]   key 是 str、value 任意类型的字典（Any = 任意类型）
# str | None       "字符串 或 None"（旧写法 Optional[str]，二者完全等价）
# str | int        "字符串 或 整数"

def find_user(user_id: int) -> str | None:
    """找到返回名字，找不到返回 None —— API 查询的典型签名。"""
    users: dict[int, str] = {1: "小明", 2: "小红"}
    return users.get(user_id)          # .get 找不到时正好返回 None

name = find_user(3)
if name is None:                       # 判断 None 用 is None，不用 == None
    print("用户不存在")

# ============================================================
# 2. TypedDict —— ★ LangGraph 的 State 必用这个 ★
# ============================================================
# 普通 dict 的 key 随便写，拼错了也不报错；TypedDict 给 dict 定义"字段表"，
# IDE 和框架就知道这个 dict 里应该有什么字段、什么类型。
# LangGraph 的每个节点函数接收 State、返回 State 的部分更新——全靠 TypedDict 描述。

class AgentState(TypedDict, total=False):
    # total=False 表示所有字段都是可选的（可以只填一部分）
    # 你的课件 Agentic_Rag/app/state.py 就是这么写的
    query: str
    documents: list[str]
    retrieval_round: int
    final_answer: str

# TypedDict 的"实例"就是普通 dict，只是有了类型说明
state: AgentState = {"query": "什么是 RAG?", "retrieval_round": 0}
state["documents"] = ["文档A", "文档B"]
print(f"状态: {state}")

# LangGraph 节点函数的典型形状（背下来这个模式！）：
def retrieve_node(state: AgentState) -> AgentState:
    """接收整个 state，只返回要更新的字段，LangGraph 会自动合并进 state。"""
    docs = [f"检索到的文档（第{state.get('retrieval_round', 0) + 1}轮）"]
    return {"documents": docs, "retrieval_round": state.get("retrieval_round", 0) + 1}

state.update(retrieve_node(state))     # 手动模拟 LangGraph 的合并动作
print(f"节点执行后: {state}")

# ============================================================
# 3. Literal —— 限定取值范围，LangGraph 条件路由的返回类型
# ============================================================
# Literal["a", "b"] 表示"只能是这几个值之一"。
# 课件真实用例：Agentic_Rag/app/graph.py 的条件边函数就返回 Literal[...]

def route(state: AgentState) -> Literal["retrieve", "answer"]:
    """LangGraph 条件边：根据状态决定下一个节点去哪。"""
    if state.get("documents"):
        return "answer"
    return "retrieve"

print(f"路由决定: {route(state)}")

# ============================================================
# 4. Enum / StrEnum —— 枚举，一组固定的常量
# ============================================================
# 课件真实用例：Agentic_Rag/app/schemas.py 的 RouteName(StrEnum)

class RouteName(StrEnum):              # StrEnum 的成员同时也是字符串
    DIRECT_ANSWER = "direct_answer"
    MILVUS_SEARCH = "milvus_search"

r = RouteName.MILVUS_SEARCH
print(f"枚举成员: {r!r}, 值: {r.value}, 可直接当字符串用: {r == 'milvus_search'}")

# ============================================================
# 5. @dataclass —— 轻量数据容器（自动生成 __init__）
# ============================================================
# 写普通类要手写 __init__ 挨个 self.x = x；dataclass 帮你自动生成。

@dataclass
class ToolResult:
    tool: str
    status: str = "ok"                                  # 带默认值
    evidence: list[str] = field(default_factory=list)   # ★ 可变默认值必须用 default_factory
    # 为什么？如果写 evidence: list = [] ，所有实例会共享同一个列表——经典大坑！

tr = ToolResult(tool="web_search", evidence=["结果1"])
print(f"\ndataclass: {tr}")            # 自动有漂亮的 __repr__
print(f"取字段: {tr.tool}, {tr.status}")

# ============================================================
# 6. Pydantic BaseModel —— ★ Agent 结构化输出的核心 ★
# ============================================================
# dataclass 只"装数据"；Pydantic 还会"校验数据"：类型不对就报错、能从 JSON 直接解析。
# LLM 返回的 JSON 用 Pydantic 一验，字段缺了/类型错了立刻发现。
# 课件真实用例：Agentic_Rag/app/schemas.py 的 RouteDecision

from pydantic import BaseModel, Field

class RouteDecision(BaseModel):
    needs_retrieval: bool
    routes: list[RouteName] = Field(default_factory=list)
    confidence: str = "medium"
    filters: dict[str, Any] = Field(default_factory=dict)

# 场景：LLM 返回了一段 JSON 字符串，解析并校验它
llm_output = '{"needs_retrieval": true, "routes": ["milvus_search"], "confidence": "high"}'
decision = RouteDecision.model_validate_json(llm_output)   # 一行完成 解析+校验+类型转换
print(f"\nPydantic 解析结果: {decision}")
print(f"取字段: needs_retrieval={decision.needs_retrieval}, routes={decision.routes}")
print(f"转回 dict: {decision.model_dump()}")

# 校验失败会抛异常——这正是它的价值：
from pydantic import ValidationError
try:
    RouteDecision.model_validate_json('{"needs_retrieval": "不是布尔值!!"}')
except ValidationError as e:
    print(f"校验失败（这是好事，帮我们拦住了 LLM 的坏输出）:\n{e.errors()[0]['msg']}")

# ============================================================
# 三者怎么选？（面试/读代码都用得上）
# ------------------------------------------------------------
# TypedDict  : 描述"就是个 dict"的形状     -> LangGraph State
# @dataclass : 内部轻量数据容器，不需校验   -> 依赖注入、配置对象
# BaseModel  : 需要校验/序列化的外部数据    -> LLM 结构化输出、API 请求响应
# ============================================================

# ============================================================
# 练习
# ============================================================
# 练习1：定义 TypedDict 类 ChatState（total=False），字段：
#        messages: list[dict]、turn: int；创建一个实例并打印
# 练习2：定义 Pydantic 模型 ToolCall：name: str、args: dict[str, Any] = Field(default_factory=dict)
#        用 model_validate_json 解析 '{"name": "calculator", "args": {"x": 1}}' 并打印 .name
# 练习3：写函数 grade(score: int) -> Literal["pass", "fail"]，score >= 60 返回 "pass"

# 在这里写你的答案：



# ------------------ 参考答案 ------------------
# class ChatState(TypedDict, total=False):
#     messages: list[dict]
#     turn: int
# cs: ChatState = {"messages": [], "turn": 1}
# print(cs)
#
# class ToolCall(BaseModel):
#     name: str
#     args: dict[str, Any] = Field(default_factory=dict)
# tc = ToolCall.model_validate_json('{"name": "calculator", "args": {"x": 1}}')
# print(tc.name)
#
# def grade(score: int) -> Literal["pass", "fail"]:
#     return "pass" if score >= 60 else "fail"
# print(grade(75))
