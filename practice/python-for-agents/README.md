# Python for AI Agents — 1 小时速成

> 本项目根据你 C:\workspace 下真实课程代码（a2a、Agentic_Rag、Multi-Agent、ai-example、ai-agent、p1）
> 中**实际出现的语法**定制，不学用不到的东西。

## 用法

每个 lesson 都是可直接运行的 Python 文件，**边看注释边运行**：

```bash
cd C:\workspace\python-for-agents
python lessons/01_basics.py
```

每个文件末尾有 2~3 道小练习（带参考答案），做完再进下一课。

## 1 小时时间表

| 时间 | 文件 | 内容 | 对应你课件里的哪些代码 |
|---|---|---|---|
| 0-10 min | `lessons/01_basics.py` | f-string、dict/list、`.get()`、切片、环境变量、`if __name__` | `p1/prompt.PY` |
| 10-20 min | `lessons/02_functions_classes.py` | 函数注解、默认参数、`**kwargs`、类与 `self`、`try/except`、`with` | `Multi-Agent/agent.py`、`tools.py` |
| 20-32 min | `lessons/03_typing_models.py` | `TypedDict`、`Literal`、`X \| None`、`Enum`、`@dataclass`、Pydantic | `Agentic_Rag/app/schemas.py`、`state.py` |
| 32-40 min | `lessons/04_comprehensions.py` | 列表推导式（过滤/展平/配对）、`enumerate`、`zip` | `Agentic_Rag/app/graph.py` |
| 40-48 min | `lessons/05_decorators.py` | 装饰器原理、`@tool` 注册工具的套路 | `ai-example/08_multi_agent/supervisor_demo.py`、`06_mcp` |
| 48-55 min | `lessons/06_async.py` | `async def` / `await` / `asyncio.gather` | `a2a/server.py`、`MemoryAgents/backend` |
| 55-60 min | `mini_agent.py` | **综合项目**：手写一个无框架迷你 Agent，把以上语法全部串起来 | `Multi-Agent/agent.py` 的简化版 |

## 优先级速查（哪些必须会、哪些可跳过）

**★ 必须会（你的课件代码几乎每个文件都有）**
f-string、dict/list 操作、函数类型注解、`if __name__ == "__main__"`、模块导入、`os.getenv`

**★ 高频（读 Agent 代码离不开）**
类与 `self`、`try/except`、列表推导式、`TypedDict`（LangGraph State 必用）、
Pydantic `BaseModel`（结构化输出必用）、装饰器（`@tool` / `@app.get`）、`**kwargs` 解包

**★ 集中出现（只在 a2a 和 MemoryAgents 用，学到那再精读）**
`async / await`

**✗ 可以不学（你的全部课件代码中几乎为 0）**
lambda、生成器/yield（除固定模板）、字典推导式、元类、`match` 语句、`functools` 高阶用法

## 配套笔记

详细知识点 + 真实来源见 [`Python语法学习笔记.md`](Python语法学习笔记.md)。
