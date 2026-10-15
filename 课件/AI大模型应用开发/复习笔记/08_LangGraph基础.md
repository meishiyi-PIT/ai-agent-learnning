# LangGraph 基础：用图式思维构建大模型 Agent 复习笔记
> 对应课件：`1. LangGraph 实战：用图式思维构建大模型 Agent.md`

---

## 一、在知识体系中的位置

**前置依赖（学这一篇前必须先懂）**

- **LangChain 基础**：Prompt、Message（HumanMessage / AIMessage / ToolMessage）、`ChatOpenAI` 这类聊天模型的 `.invoke()`。LangGraph 复用了这些底层组件。
- **Function Calling / 工具调用**：知道"把工具描述塞进模型请求，模型返回 `tool_calls`，我们再去执行"这一套协议。第九篇 ReAct 会大量用到。
- **Python 中级语法**：`TypedDict`、`Annotated`、装饰器、`dataclass`。第五节会逐个补。

**本篇讲了什么（课件骨架）**

```
三块积木         State（全局状态） + Node（干活的函数） + Edge（路由的边）
   ↓
最简图 → 条件边/循环 → 状态管理（覆盖 vs reducer / MessagesState / 自定义 reducer）
   ↓
图的组合         子图（黑盒复用） + Send（动态 fan-out 并行）
   ↓
记忆             Checkpointer（会话内短期记忆） + Store（跨会话长期记忆）
   ↓
运行时           Context / Runtime / RunnableConfig（谁在调用、什么配置）
   ↓
六步法 + 实战：天气助手 Agent
```

**往后连到哪里**

```
本篇（LangGraph 基础）
  └─→ 09 ReAct 与 Plan-and-Execute：把"LLM 节点 + 工具节点 + 条件边"
  │     这套循环封装成 create_agent，再拼出多步规划
  └─→ 10 Middleware：给 create_agent 的执行循环插"治理层"
  └─→ Multi-Agent 编排、Agentic RAG：都是在 LangGraph 的图上
        把"检索器 / 子 Agent"当成一个节点接进去
```

一句话定位：**这是整个"企业级 Agentic AI 开发"模块的地基。把 State / Node / Edge / Checkpointer 这四个概念真正吃透，后面所有 Agent 花活都只是这四样东西的排列组合。**

---

## 二、核心知识点精讲

### 1. 为什么要用"图"，而不是"链"

LangChain 的 `Chain` 是一条**单向水管**：Prompt → LLM → 解析器，数据从头流到尾，走的是**有向无环图（DAG）**——没有回头路。

但真实 Agent 要做三件 Chain 做不了的事：

- **循环**：模型调了一次工具发现信息不够，得再调一次。
- **条件分支**：下雨走"室内推荐"，不下雨走"户外推荐"。
- **动态决策**：根据对话历史临时决定走哪条链路。

LangGraph 的答案：**把工作流建模成一张有向图**。节点是处理步骤，边是流转关系，一个全局 State 贯穿始终。循环？加一条往回指的边。分支？加条件边。

> 类比：Chain 是拼水管（只能顺流），LangGraph 是画电路图（可以有回路、有开关）。

**LangGraph 和 LangChain 的关系**：LangGraph 是 LangChain 生态里的**独立模块**，共享底层组件（Message、PromptTemplate），但图式编程模型完全独立。你甚至可以让节点是纯 Python 函数，一行 LangChain 都不碰。

### 2. 三块积木

| 积木 | 是什么 | 关键点 |
| --- | --- | --- |
| **State** | 全局共享的运行时数据（TypedDict / Pydantic） | 所有节点都能读、都能写 |
| **Node** | 一个 Python 函数 `(state) -> dict` | 只返回"要更新的字段"，没返回的保持不变 |
| **Edge** | 决定"下一步去哪" | 普通边（直连）/ 条件边（按 State 选路） |

**Node 的输入输出，务必记牢**：

```python
def my_node(state: StateType) -> dict:
    result = do_something(state)
    return {"field_to_update": result}   # 只返回增量，不是整个 State
```

输入是**完整的当前 State**，输出是**部分更新字典**。这个"只返回增量"的设计，是后面 reducer 机制的前提。

### 3. 条件边的本质：路由函数 + 白名单

条件边由两部分组成：一个**路由函数**（返回下一个节点的名字字符串），加一个**路由映射（白名单）**。

```python
def router(state) -> str:
    if state["count"] >= 5:
        return END           # 特殊常量，代表"出口"
    return "increment"       # 回到 increment 节点 → 形成循环

builder.add_conditional_edges(
    "increment",                              # 从哪个节点出发
    router,                                   # 用哪个函数决定方向
    {"increment": "increment", END: END},     # 返回值 → 目标节点的映射（白名单）
)
```

**为什么要有白名单？** 它是防御性设计：如果 router 返回了不在白名单里的名字（比如拼错了），LangGraph 立刻抛异常，而不是让图跑到一个不存在的节点去。`START` / `END` 是两个虚拟节点常量，代表入口和出口。

> 深入一点：第三个参数（path_map）其实可以省略。省略时，router 返回的字符串会**直接当作节点名**。写上映射的价值是：① 显式声明合法目标，② 让 `router` 返回业务语义值（如 `"high"/"low"`）再映射到具体节点，解耦。

### 4. 状态更新：覆盖 vs 追加（reducer 是核心中的核心）

这是 LangGraph 最容易糊涂、也最该讲透的地方。

**默认行为 = 覆盖（last write wins）**：节点返回什么，字段就变成什么。

```python
class OverwriteState(TypedDict):
    items: list[str]
# node_a 返回 {"items": ["a1"]} → items = ["a1"]
# node_b 返回 {"items": ["b1"]} → items = ["b1"]（把 a 的结果覆盖了）
```

**想追加，就用 `Annotated` 声明 reducer**：

```python
from typing import Annotated, TypedDict
from operator import add

class AppendState(TypedDict):
    items: Annotated[list[str], add]   # 第二个位置放的 add 就是 reducer
```

底层逻辑：**每次节点返回 `{"items": [...]}`，LangGraph 都会执行 `reducer(旧值, 新值)`**。对 `operator.add` 而言就是 `旧list + 新list`，于是不断追加。

关键澄清（课件一笔带过、但必须懂）：**reducer 不是只在"并行合并"时才触发**。哪怕是单条路径顺序执行，每个节点返回该字段时都会走一遍 reducer。"覆盖"其实就是 LangGraph 给无 `Annotated` 字段用的默认 reducer。

### 5. MessagesState 与 `add_messages`

对话是最高频场景，LangGraph 预置了 `MessagesState`：

```python
# MessagesState 内部等价于：
# messages: Annotated[list, add_messages]
```

`add_messages` 是一个**专为消息设计的智能 reducer**，和 `operator.add` 差别很大：

| 维度 | `operator.add` | `add_messages` |
| --- | --- | --- |
| 行为 | 纯拼接 | 智能合并 |
| 去重 | 不去重 | **相同 id 的消息会替换旧的** |
| 类型转换 | 不转换 | 自动把 `(role, content)` 元组转成 Message 对象 |
| 适用 | 数字/字符串列表 | **对话消息列表** |

一句话：**存聊天消息用 `add_messages`，其他用 `add` 或自定义 reducer**。要加别的字段，直接继承：

```python
class MyAgentState(MessagesState):
    user_name: str
    tool_call_count: int
```

### 6. 自定义 reducer

reducer 本质是一段"冲突解决逻辑"，签名固定为 `(旧值, 新值) -> 合并结果`。课件用一个"平时追加、偶尔全量替换"的例子演示：靠一个带 `replace` 标记的 `list` 子类，让 reducer 判断该拼接还是覆盖。要点只有一个：**声明式地把合并规则写在 State 定义里，比在每个节点里写 if-else 干净得多。**

### 7. 子图：把复杂逻辑装进黑盒

子图 = 把一组步骤编译成一张图，再在主图里当**一个普通节点**用，就像把一段逻辑抽成函数。好处是封装复用 + 关注点分离。课件的"泡咖啡"例子里，子图用**独立的 State schema**（`SubCoffeeState`），在主图的包装节点里手动做状态映射（`sub_result["sub_logs"]` → 主图的 `logs`）。

> 注意：子图和主图共用一套 State 时可以直接 `add_node("make", coffee_subgraph)`；用不同 schema 时就得像课件那样包一层函数做字段映射。

### 8. Send：运行时的动态并行（fan-out）

**Send 用来解决"编译时不知道要并行几个"的问题**。典型场景：用户说"对比苹果、华为、小米"——几个品牌运行时才知道，就发几个并行任务。

```python
from langgraph.types import Send

def route_to_research(state):
    return [
        Send("research_brand", {"brands": [brand]})   # 目标节点 + 该分支专属 state
        for brand in state["brands"]
    ]
```

四条铁律：
1. **Send 只能出现在 `add_conditional_edges` 的路由函数返回值里**。
2. 路由函数不能同时当 `add_node` 的节点函数。
3. 返回 Send 列表 → 并行；返回空列表 / END → 停。
4. 并行结果靠 State 里的 `Annotated + reducer` 自动合并（所以 `reports` 要写成 `Annotated[list, add]`）。

**什么时候用**：并行任务数运行时才定 → 用 Send；写代码时就固定（永远 3 条分支）→ 直接画 3 条边。

### 9. 给 Agent 装记忆：Checkpointer vs Store

这是本篇最有生产价值的一节。

**Checkpointer（会话内短期记忆）**：在图的每个"超步"执行完后自动存一个 State 快照。同一个 `thread_id` 的后续调用从快照继续，于是模型能看到之前几轮的完整历史。

```python
from langgraph.checkpoint.memory import InMemorySaver
graph = builder.compile(checkpointer=InMemorySaver())   # ★ 关键
config = {"configurable": {"thread_id": "session-001"}}  # thread_id 标识会话
graph.invoke({"messages": [...]}, config=config)
```

- **线程隔离**：不同 `thread_id` 之间完全隔离，这是设计意图（每个用户/会话独立记忆）。实用建议：`thread_id = f"user_{uid}:chat_{sid}"`。
- **`get_state_history()`**：调试神器，能列出每一步执行后的 State 快照（时间倒序，`[0]` 最新）。
- **生产要换持久化**：`InMemorySaver` 进程一重启记忆就没了，线上要用 `RedisSaver`（`langgraph-checkpoint-redis` 包）/ `PostgresSaver` / `SqliteSaver`。

**Store（跨会话长期记忆）**：Checkpointer 管"同一会话内"，Store 管"跨会话"——用户上周说的话、"记住我叫老王"这类用户档案。数据模型是 `namespace → key → value`：

```python
store.put(("memories", "user_42"), str(uuid.uuid4()), {"data": "用户叫老王"})
results = store.search(("memories", "user_42"), query="用户的名字")
```

| 需求 | 用什么 |
| --- | --- |
| 同一会话内的消息历史 | Checkpointer |
| 跨会话的用户偏好/档案 | Store |
| 临时工作流状态 | State（不持久化） |

> ⚠️ 课件在这里有个**会误导人的坑**：直接 `InMemoryStore()` 然后 `search(query=...)` 并声称"内置向量搜索、不需要额外向量数据库"。实际上语义搜索默认是**关闭**的，必须配置嵌入模型才生效。详见第三节勘误。

### 10. Context / Runtime：把"谁在调用"传进节点

有些信息不属于对话业务（user_id、权限等级、模型配置），不该塞进 State。LangGraph 1.0 用 **Context + Runtime** 传这类运行时信息：

```python
@dataclass
class Context:
    user_id: str

def chat_node(state: MessagesState, runtime: Runtime[Context]):
    uid = runtime.context.user_id        # 拿外部注入的上下文
    mems = runtime.store.search(...)     # runtime 也是访问 Store 的入口
    ...

builder = StateGraph(MessagesState, context_schema=Context)
graph = builder.compile(store=store)
graph.invoke({...}, context=Context(user_id="user_42"))
```

**记住**：不在节点签名里声明 `runtime: Runtime[Context]`，你就拿不到 context 和 store——它们已经注入了，只是你没开"入口"。另外 `RunnableConfig`（`config={"configurable": {...}}`）是更老、更灵活的一套：`thread_id`、`checkpoint_id` 走这里，也能塞任意自定义字段供节点/工具读取。

### 11. 标准六步法

```
① 定义模型与工具 → ② 定义 State → ③ 实现节点函数
→ ④ 构建图（加节点、连边） → ⑤ 编译（注入 Checkpointer/Store） → ⑥ 执行（invoke/stream）
```

不是教条，但迷路时可以用它定位"我走到哪一步了"。

---

## 三、课件勘误与更新

> 说明：本篇课件写于 2026 年，模型名 `deepseek-v4-flash` **是真实存在的**（DeepSeek V4 于 2026-04-24 发布），所以课件用它并没有错。下面只列真正有问题的点。

### 已确认

**1）InMemoryStore 语义搜索默认关闭，课件的写法产生不了示例中的语义排序结果**

- 课件原文（6.5）：`store = InMemoryStore()` 后 `results = store.search(ns, query="用户的名字和工作")`，并注释"语义搜索记忆（Store 内置了向量搜索能力，不需要额外的向量数据库）"，输出还按语义挑出了 2 条最相关记忆。
- 问题类型：**不严谨 / 会误导**。
- 正确说法：LangGraph 的 Store **语义搜索默认是禁用的**。必须在创建时传入 `index` 配置（嵌入模型 + 维度 + 要嵌入的字段）才会真正按 `query` 做向量相似度排序；不配置时 `search` 只能做命名空间/filter 级别的返回，`query` 参数不生效。正确写法：
  ```python
  from langchain.embeddings import init_embeddings
  store = InMemoryStore(index={
      "dims": 1536,
      "embed": init_embeddings("openai:text-embedding-3-small"),
      "fields": ["data"],
  })
  ```
  也就是说，语义检索**确实需要一个嵌入模型**（相当于一个轻量向量库），课件"不需要额外向量数据库"的表述容易让学员以为开箱即用。
- 来源：https://github.com/langchain-ai/langgraph/blob/main/docs/docs/concepts/persistence.md ；https://blog.langchain.com/semantic-search-for-langgraph-memory/

**2）最简图示例传入了 State 里不存在的字段**

- 课件原文（3.1）：`CounterState` 只定义了 `count`，但执行时写 `graph.invoke({"count": 1, "log": []})`。
- 问题类型：**不严谨（代码自身不一致）**。`log` 不在 schema 里，属多余字段，容易让读者以为 State 有个 `log`。这是课件内部笔误，非 API 问题，故不单独给外链，改在"没讲透"里说明 State schema 会约束字段。

### 待核实

- **`RedisSaver.from_conn_string(...)` + `checkpointer.setup()` 的确切用法**：不同版本的 `langgraph-checkpoint-redis` 在 `setup()` 是否必需、是否要用 `with` 上下文管理器上略有差异，课件示例大方向正确，但精确签名建议以你安装的版本为准，未逐版本核实。
- **`context_schema` / `Runtime[Context]` / `graph.invoke(..., context=...)`**：这是 LangGraph 0.6+ 到 1.0 的较新 Runtime API，课件用法与 1.0 一致；但更早版本用的是 `config_schema` + `config`，如果你装的是旧版可能报 `context` 不被识别，需按版本对照。

---

## 四、课件没讲透的关键点补充

**1）reducer 的触发时机（不止并行）**
每个节点每次返回某字段，都会走一遍该字段的 reducer——包括顺序执行。"覆盖"就是无 `Annotated` 字段的默认 reducer。真正理解这点，才明白为什么 `messages` 会自动累积、为什么 Send 的并行结果能自动拼起来。

**2）无 reducer 字段 + 并行写 = 报错**
课件"坑 1"只说了 `add` 会重复，但没说：如果两个**并行**分支同时写一个**没有 reducer** 的字段，LangGraph 会抛 `InvalidUpdateError`（它不知道该听谁的）。所以并行分支要么写不同字段，要么给共享字段配 reducer。

**3）super-step（超步）与 checkpoint 的对应关系**
LangGraph 按"超步"推进：同一超步内的节点（含 Send 并行出来的）并行跑，跑完统一用 reducer 合并、存一次 checkpoint。所以 `get_state_history()` 里一个快照 = 一个超步，而不是一个节点。

**4）条件边可以返回三类东西**
路由函数返回值可以是：① 节点名字符串、② `END`、③ `Send` 列表（并行）。搞混"节点函数返回 dict"和"路由函数返回字符串/Send"是新手高频错误。

**5）`compile()` 的意义**
`compile()` 之前图只是"模板"（builder），之后才是可执行实例。Checkpointer / Store / interrupt 都是在 `compile()` 这一步注入的。

**6）START/END 是常量不是字符串**
从 `langgraph.graph` 导入。`END` 在映射里当 key 用（`{END: END}`）没问题，因为它本质是特殊字符串常量。

---

## 五、Python 随堂补基础

**① TypedDict —— 给字典规定"有哪些键、各是什么类型"**
```python
from typing import TypedDict
class CounterState(TypedDict):
    count: int
s: CounterState = {"count": 1}   # 本质还是 dict，只是有类型提示；多传的键不在 schema 内
```

**② `Annotated[类型, 元数据]` —— 给类型"贴标签"**
```python
from typing import Annotated
from operator import add
# 第一个是真正的类型(list[str])，第二个是给 LangGraph 读的元数据(reducer)
items: Annotated[list[str], add]
```
Python 本身不管第二个参数，是 LangGraph 去读它当 reducer。

**③ 泛型 `list[str]` / `dict[str, int]` —— 标注容器里装什么**
```python
names: list[str] = ["a", "b"]        # 一个装字符串的列表
scores: dict[str, int] = {"x": 1}    # 键是 str、值是 int
```

**④ `dataclass` —— 几行代码定义一个"数据类"**
```python
from dataclasses import dataclass
@dataclass
class Context:
    user_id: str
    tier: str = "free"     # 带默认值
c = Context(user_id="alice")   # 自动生成 __init__
```

**⑤ 类继承 —— MessagesState 加字段**
```python
class MyState(MessagesState):   # 继承已有字段(messages)，再补自己的
    user_name: str
```

**⑥ 生成器 / 流式 for 循环 —— 边产生边消费**
```python
for chunk in graph.stream({"messages": [...]}, config):
    print(chunk)   # 每产出一步就处理一步，不用等全部跑完
```

---

## 六、自测清单

**是什么（概念）**
1. State、Node、Edge 各自是什么？Node 函数的输入和输出分别是什么？
2. 普通边和条件边的区别是什么？`add_conditional_edges` 的第三个参数（白名单）有什么用？
3. `START` / `END` 是什么？
4. Checkpointer 和 Store 各解决"哪种记忆"？
5. `MessagesState` 里的 `messages` 字段用的是哪个 reducer？

**为什么（原理）**
6. 为什么 State 更新默认是"覆盖"？想改成"追加"要怎么做？
7. `operator.add` 和 `add_messages` 都能合并列表，为什么存消息一定要用 `add_messages`？
8. reducer 到底在什么时候被调用？只有并行时才触发吗？
9. 为什么 `InMemoryStore()` 直接 `search(query=...)` 拿不到真正的语义排序结果？
10. 为什么两个并行分支同时写一个没有 reducer 的字段会报错？

**什么时候用（决策）**
11. 什么时候用 Send，什么时候直接画固定的并行边？
12. 什么时候把逻辑拆成子图？
13. 一个信息该放 State 还是放 Context（Runtime）？判断标准是什么？
14. 开发用 `InMemorySaver`，上线前必须改成什么？漏改会出现什么现象？

---

## 七、动手小练习

**练习 A（20 分钟）：带循环的累加图**
写一个 State 只含 `count: int` 的图：节点 `increment` 每次 +1；用条件边判断——`count < 5` 回到 `increment`，`>= 5` 走 `END`。跑通后，用 `graph.get_graph().draw_mermaid_png()`（或直接看 `draw_mermaid()` 文本）确认它画出了一个自循环。
> 目标：吃透"条件边 + 循环"和"路由函数返回节点名/END"。

**练习 B（30 分钟）：给聊天机器人加记忆**
用 `MessagesState` + 一个 `chat` 节点（调 `ChatOpenAI`）搭最简聊天图，`compile(checkpointer=InMemorySaver())`。用同一个 `thread_id` 连问两轮：第一轮"我叫小李，是做前端的"，第二轮"我叫什么？做什么工作？"，验证它记得住。再换一个 `thread_id` 问同样问题，验证记忆是隔离的。
> 目标：亲手体验 Checkpointer + thread_id + 线程隔离。（模型名用当前可用的 `deepseek-v4-flash`，别用已下线的 `deepseek-chat`。）

---

## 来源链接
- LangGraph 持久化与 Store 语义搜索配置：https://github.com/langchain-ai/langgraph/blob/main/docs/docs/concepts/persistence.md
- Semantic Search for LangGraph Memory（需 index/embeddings）：https://blog.langchain.com/semantic-search-for-langgraph-memory/
- LangGraph v1 迁移指南（context_schema / Runtime 等新 API）：https://docs.langchain.com/oss/python/migrate/langgraph-v1
- DeepSeek 模型与更新日志（deepseek-v4-flash / deepseek-chat 下线）：https://api-docs.deepseek.com/updates/
