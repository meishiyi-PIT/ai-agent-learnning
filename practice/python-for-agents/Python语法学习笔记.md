# Python 语法学习笔记（AI Agent 方向定制）

> 生成日期：2026-07-25
> 依据：对 C:\workspace 下约 90 个课程 .py 文件（a2a、Agentic_Rag、ai-agent、ai-example、Multi-Agent、p1）的语法特性扫描。
> 结论先行：**你不需要"系统学 Python"，只需要掌握下面这张表里 ★3 以上的条目**，即可读懂全部课件代码。

---

## 一、优先级总表（按你课件中的真实出现频率排序）

| 优先级 | 语法点 | 在哪个课件代码里最典型 | 对应练习 |
|---|---|---|---|
| ★★★★★ | f-string（含 `:.2f` 格式化、`[:60]` 切片） | 所有文件 | lessons/01 |
| ★★★★★ | dict/list 操作、`.get(k, 默认值)`、消息列表 | 所有 LLM 调用代码 | lessons/01 |
| ★★★★★ | 函数类型注解 `def f(x: str, k: int = 5) -> str` | 所有文件 | lessons/02 |
| ★★★★★ | 模块导入、`os.getenv` + `load_dotenv`、`if __name__` | `p1/prompt.PY` | lessons/01 |
| ★★★★☆ | 类、`__init__`、`self` | `Multi-Agent/agent.py` | lessons/02 |
| ★★★★☆ | `try/except Exception as e` | `Multi-Agent/tools.py` | lessons/02 |
| ★★★★☆ | 列表推导式（过滤/展平/配对） | `Agentic_Rag/app/graph.py:127-148` | lessons/04 |
| ★★★★☆ | `TypedDict`（LangGraph State 必用） | `Agentic_Rag/app/state.py:8-23` | lessons/03 |
| ★★★★☆ | Pydantic `BaseModel` + `Field(default_factory=...)` | `Agentic_Rag/app/schemas.py:9-28` | lessons/03 |
| ★★★★☆ | 装饰器 `@tool` / `@mcp.tool()` / `@app.get` | `ai-example/08_multi_agent/supervisor_demo.py:64-81` | lessons/05 |
| ★★★☆☆ | `**kwargs` / `fn(**dict)` 解包 | `Multi-Agent/agent.py:22-65` | lessons/02、05 |
| ★★★☆☆ | `Literal[...]`、`X \| None`、`Enum/StrEnum`、`@dataclass` | `Agentic_Rag/app/schemas.py`、`graph.py` | lessons/03 |
| ★★★☆☆ | `enumerate` / `zip(…, strict=True)`、`with` 语句 | `Agentic_Rag/app/graph.py`、`Multi-Agent/tools.py` | lessons/02、04 |
| ★★★☆☆ | `async/await`（**只集中在 a2a 和 MemoryAgents**） | `a2a/server.py:38-48` | lessons/06 |
| ★★☆☆☆ | `ABC`/`@abstractmethod`/`Protocol`（适配器模式） | `ai-example/MemoryAgents/backend/app/adapters/base.py` | 读到再学 |
| ✗ 不用学 | lambda、生成器/yield、字典推导、元类、match、functools | 课件中几乎为 0 | — |

---

## 二、核心知识点速记（每条附最小示例）

### 1. f-string —— prompt 拼装的唯一姿势
```python
name, score = "RAG", 0.876
f"主题 {name}，得分 {score:.1%}"     # -> '主题 RAG，得分 87.6%'
f"预览: {long_text[:60]}..."         # 切片截断，日志里最常见
```
来源：[Python 官方教程 §7.1 f-string](https://docs.python.org/zh-cn/3/tutorial/inputoutput.html#formatted-string-literals)

### 2. dict.get —— 读不确定存在的字段不崩溃
```python
timeout = config.get("timeout", 30)    # 没有这个 key 时返回 30，而不是 KeyError
```
LLM 响应、State 里的可选字段全用它。来源：[dict.get 文档](https://docs.python.org/zh-cn/3/library/stdtypes.html#dict.get)

### 3. 类型注解 —— 不是摆设，框架靠它干活
```python
def get_weather(city: str, days: int = 3) -> str: ...
```
MCP / LangChain 会读取注解自动生成工具参数 schema，**注解写错，LLM 传参就错**。
来源：[typing 官方文档](https://docs.python.org/zh-cn/3/library/typing.html)

### 4. TypedDict —— LangGraph State 的标准写法
```python
class AgentState(TypedDict, total=False):   # total=False: 字段全部可选
    query: str
    documents: list[str]
```
LangGraph 节点函数 = 接收 State、返回"部分更新 dict"，框架负责合并。
来源：[PEP 589](https://peps.python.org/pep-0589/)、你的 `Agentic_Rag/app/state.py`

### 5. Pydantic BaseModel —— 拦住 LLM 的坏输出
```python
class Decision(BaseModel):
    action: Literal["call_tool", "final_answer"]
    args: dict[str, Any] = Field(default_factory=dict)

Decision.model_validate_json(llm_output)   # 解析+校验+类型转换一步到位，错了抛 ValidationError
```
⚠️ 大坑：可变默认值必须 `Field(default_factory=list)`，写 `= []` 所有实例共享同一列表。
来源：[Pydantic 官方文档](https://docs.pydantic.dev/latest/)

### 6. 列表推导式三形态（graph.py 数据加工主力）
```python
[d.strip() for d in docs]                                  # 变换
[r["tool"] for r in results if r["status"] == "error"]     # 过滤
[item for batch in batches for item in batch]              # 展平（双 for 从左到右读）
```
来源：[官方教程 §5.1.3](https://docs.python.org/zh-cn/3/tutorial/datastructures.html#list-comprehensions)

### 7. 装饰器 —— @tool 的本质是"登记 + 读元数据"
```python
@tool                       # 等价于 divide = tool(divide)
def divide(a: float, b: float):
    """除法工具。"""         # docstring 会被当作工具描述发给 LLM
```
记住三位一体：**装饰器注册 + 类型注解生成参数 schema + docstring 生成描述**。
`@mcp.tool()` 带括号 = 先调用返回装饰器（多一层）。
来源：[PEP 318](https://peps.python.org/pep-0318/)、你的 `ai-example/06_mcp/my_mcp_server.py`

### 8. **kwargs 与解包 —— 手写 Agent 循环的关键一招
```python
def call(model: str, **kwargs): ...   # 定义处：收集多余关键字参数成 dict
client.chat.completions.create(**params)   # 调用处：dict 展开成关键字参数（方向相反）
TOOLS[name]["func"](**tool_args)           # Agent 执行工具的标准姿势
```
来源：[官方教程 §4.9](https://docs.python.org/zh-cn/3/tutorial/controlflow.html#keyword-arguments)

### 9. async / await —— 只需三句话
```python
async def f(): ...          # 定义协程；调用 f() 不执行，只得到协程对象
result = await f()          # 真正执行并等待；只能写在 async def 里
asyncio.run(main())         # 同步世界的唯一入口（FastAPI 项目里由 uvicorn 代劳）
await asyncio.gather(a(), b())   # 并发跑多个，总耗时 ≈ 最慢的那个
```
你的课件里只有 a2a 和 MemoryAgents 用异步，其余项目全同步——不必焦虑。
来源：[asyncio 官方文档](https://docs.python.org/zh-cn/3/library/asyncio-task.html)

### 10. try/except —— LLM 输出永远不可信
```python
try:
    data = json.loads(llm_output)
except json.JSONDecodeError as e:
    data = {}                        # 兜底，别让 Agent 崩
```
来源：[官方教程 §8](https://docs.python.org/zh-cn/3/tutorial/errors.html)

---

## 三、三种"数据类"怎么选（高频困惑点）

| | TypedDict | @dataclass | Pydantic BaseModel |
|---|---|---|---|
| 本质 | 带字段说明的 dict | 自动生成 `__init__` 的类 | 会校验数据的类 |
| 校验 | ✗ | ✗ | ✓（类型错误抛异常） |
| 典型用途 | LangGraph State | 内部轻量容器/依赖注入 | LLM 结构化输出、API 模型 |
| 课件出处 | `state.py` | `graph.py` 的 GraphDependencies | `schemas.py` |

---

## 四、建议的课件阅读顺序（学完 lessons 后）

1. `p1/prompt.PY` —— 全部是 Lesson 01/02 的语法，热身
2. `Multi-Agent/agent.py` + `tools.py` —— 无框架 Agent 循环（mini_agent.py 的真实版）
3. `Agentic_Rag/app/schemas.py` + `state.py` —— 类型系统实战
4. `ai-example/08_multi_agent/supervisor_demo.py`、`06_mcp/my_mcp_server.py` —— @tool 套路
5. `a2a/server.py` —— 异步实战
6. `Agentic_Rag/app/graph.py` —— 终极综合（推导式 + Literal + dataclass + 条件路由）

## 五、查漏补缺记录（学习中遇到不懂的记在这里）

- [ ] （示例）`raise ... from exc` 是什么？→ 异常链：保留原始异常信息，见 [官方文档](https://docs.python.org/zh-cn/3/tutorial/errors.html#exception-chaining)
- [ ]
