# LangGraph / LangChain Middleware 复习笔记
> 对应课件：`3. LangGraph实战：Middleware.md`

---

## 一、在知识体系中的位置

**前置依赖（学这一篇前必须先懂）**

- **09 笔记**：`create_agent`、ReAct 循环里的"模型调用 → 工具调用"节奏、`interrupt_before` 手写断点。Middleware 里的很多内置能力，本质是把 09 篇"手写的治理逻辑"标准化、声明式化了。
- **08 笔记**：State（`AgentState` 是它的一种）、Runtime（`runtime.context` / `runtime.store`）、Checkpointer（`HumanInTheLoopMiddleware` 强依赖它）。
- **Python 中级语法**：装饰器（`@before_model` 这类）、类继承（`AgentMiddleware`）、闭包/全局变量（重试计数器）。第五节会补。

**本篇讲了什么（课件骨架）**

```
一、架构认知      六大钩子点（before_agent/before_model/wrap_model_call/
                  after_model/wrap_tool_call/after_agent）+ request/handler/state/runtime
二、安全风控      次数限制（Model/ToolCallLimit）+ 人工确认（HITL）+ PII 脱敏
三、稳定性治理    重试/降级（Retry/Fallback）+ 长对话摘要 + 工具结果清理
四、自定义进阶    装饰器模式 vs 类模式 + 动态 Prompt
```

**往后连到哪里**

```
本篇（Middleware）
  └─→ Multi-Agent 编排：每个子 Agent 都可以套一层 Middleware 栈，
        治理逻辑（限流/脱敏/审批）在多智能体场景下更需要统一管理
  └─→ 生产部署：本篇"生产级 Middleware 栈"示例就是上线前的检查清单
```

一句话定位：**08 篇教你怎么搭图，09 篇教你怎么用图跑通 Agent 范式，本篇教你怎么在不碰业务代码的前提下，把"治理"（限流、审批、脱敏、重试、摘要）作为一层横切关注点插进 Agent 的执行循环。**

---

## 二、核心知识点精讲

### 1. 为什么需要 Middleware：职责分离

一个 Agent 一旦上线，光靠 System Prompt 里"多写两句话"防不住这几类问题：无限循环烧 Token、越权操作、隐私信息直接喂给模型、外部依赖抽风。这些问题的共同点是：**它们和"业务逻辑对不对"无关，而是"这次调用该不该发生、发生的时候要不要被管控"**。

Middleware 的定位：**业务逻辑写在工具里，治理逻辑写在 Middleware 里**——不改变 Agent 做业务的方式，但在它做业务的时候盯着、拦着、兜着底。这是典型的"横切关注点"（cross-cutting concern）设计，和 Web 框架里的中间件（鉴权、日志、限流）是同一个思路。

### 2. 六大钩子点：Middleware 在哪些时机介入

| 钩子 | 触发时机 | 典型用途 |
| --- | --- | --- |
| `before_agent` | Agent 启动前 | 初始化状态、检查前置条件 |
| `before_model` | 每次调模型之前 | 审计日志、脱敏、状态检查 |
| `wrap_model_call` | **包裹**模型调用过程 | 重试、降级、模型切换 |
| `after_model` | 模型返回之后 | 记录响应、检测 tool_calls、更新计数 |
| `wrap_tool_call` | **包裹**工具调用过程 | 权限校验、参数拦截、耗时统计 |
| `after_agent` | Agent 执行结束后 | 清理状态、发送通知 |

**`before_*`/`after_*` 和 `wrap_*` 的本质区别**，课件没有明说，但从代码能看出来：
- `before_model` / `after_model` / `before_agent` / `after_agent` 是**单点钩子**：函数签名 `(state, runtime) -> dict | None`，返回 `None` 表示不修改，返回 `dict` 会浅合并进 state。它们**不能决定"要不要真正发生这次调用"**，只能在调用前后做旁路操作。
- `wrap_model_call` / `wrap_tool_call` 是**包裹型钩子**：函数签名 `(request, handler) -> result`，`handler` 就是"真正执行这一步"的入口。**不调用 `handler`，这次模型调用/工具调用就不会发生**——所以拦截、替换、重试、降级这类"决定要不要发生"的逻辑，必须用 `wrap_*`，而不是 `before_*`/`after_*`。

一条必须刻在脑子里的安全规则：**不调 `handler` = 原始操作从未发生；调两次 `handler` = 操作执行两次**——对发邮件、扣款这类操作，重复调用可能是事故级问题。

### 3. `request` / `handler`：单次调用视角

**`ToolCallLimitRequest`（`@wrap_tool_call` 拿到的 `request`）关键字段**：

| 字段 | 含义 |
| --- | --- |
| `request.tool_call["name"]` | 模型决定调哪个工具 |
| `request.tool_call["args"]` | 模型生成的调用参数 |
| `request.tool_call["id"]` | 本次调用的唯一 ID（构造 `ToolMessage` 时要用它做 `tool_call_id`） |
| `request.tool` | 工具对象本身 |
| `request.state` / `request.runtime` | 同全局的 state/runtime |

`handler(request)` 之前可以做参数校验、修改参数；也可以完全不调用它，直接 `return` 一个伪造的 `ToolMessage`，相当于"假装工具执行过了，告诉模型结果是这个"——这正是 09 篇里手写 `graph.update_state()` 拦截工具调用的声明式替代方案。

**`ModelRequest`（`@wrap_model_call` 拿到的 `request`）多了这些**：`request.messages`（即将发给模型的上下文）、`request.model`、`request.tools`、`request.model_settings`。核心用法是 `request.override(model=备用模型)`——不用重建 Agent 就能临时换模型，这是"降级"类 Middleware 的底层机制。

`wrap_model_call` 在模型**每次**被调用时都触发（包括循环里的多轮）；`wrap_tool_call` 只在模型明确要求调用工具时触发。

### 4. `state` / `runtime`：全局运行视角

`state`（类型 `AgentState`）是 Agent 运行中不断累积的数据，核心是 `state["messages"]`。要追踪自定义业务指标（调用次数、拦截次数），继承 `AgentState` 扩展字段，并在装饰器上声明 `state_schema`：

```python
class ExportAgentState(AgentState):
    model_call_count: NotRequired[int]

@after_model(state_schema=ExportAgentState)
def update_stats(state, runtime):
    return {"model_call_count": state.get("model_call_count", 0) + 1}
```

`runtime.context` 是从**外部**注入、和对话内容无关的信息（请求 ID、用户角色、租户 ID），调用时传：`agent.invoke({...}, context={...})`，创建 Agent 时用 `context_schema=` 声明结构。

**必须记住的一点**：`runtime.context` **不会自动让模型看到**。它只是"你的 Middleware 代码能读到"，不代表模型知道。想让它影响模型行为，必须在 Middleware 里显式写进 state 或拼进 prompt——这正是 `@dynamic_prompt` 的用武之地。

### 5. 安全风控三件套

**次数限制**：`ModelCallLimitMiddleware`（管全局模型调用次数）+ `ToolCallLimitMiddleware`（管单个工具的调用次数），两者可以混用，任一触发都会拦截/结束。

- `run_limit`：单次 `invoke()` 内的上限。
- `thread_limit`：整个对话线程的累计上限，**必须配合 `checkpointer`**（因为要跨轮持久化计数）。
- `exit_behavior`：`"end"`（优雅结束，生成兜底回复）/ `"error"`（抛异常）/ `"continue"`（仅工具限制可用，返回限流信息让模型自己组织语言回复用户）。

**人工确认（HITL）**：`HumanInTheLoopMiddleware(interrupt_on={...})`，给每个工具单独配置是否需要审批、允许哪些审批动作（`approve`/`edit`/`reject`）。恢复执行靠 `Command(resume={"decisions": [...]})`，同一个 `thread_id` 是审批能对上号的前提，且**必须有 checkpointer**。这是 09 篇"手写人工节点"（`ask_human` 标志位 + `interrupt_before` + `as_node`）的封装版——底层机制一脉相承，用法从"自己搭图"变成"声明配置"。

**PII 脱敏**：`PIIMiddleware` 在消息进模型**之前**（也可以是工具返回之后、模型输出之后）做检测替换。内置类型有 email、credit_card（Luhn 校验）、ip、mac_address、url；中文场景常用的手机号、身份证号需要传自定义 `detector`（正则或返回 `[{"text","start","end"}]` 的函数）。四种策略：`redact`（替换占位符）/`hash`（确定性哈希，可去重）/`mask`（部分遮盖）/`block`（直接抛 `PIIDetectionError` 中断执行）。

> 注意作用域：`PIIMiddleware` 只保护 Agent 的消息管道（`apply_to_input`/`apply_to_tool_results`/`apply_to_output`），你自己在工具函数里打的日志、调用的外部 API 不在它的保护范围内。

### 6. 稳定性与上下文治理三件套

**重试与降级**：`ToolRetryMiddleware`（工具级重试）+ `ModelRetryMiddleware`（模型级重试）处理"临时性抖动"；`ModelFallbackMiddleware`（切备用模型）处理"持续性不可用"。设计理念是**重试逻辑不写进工具函数**，工具只管干活，超时重几次、间隔多久由 Middleware 统一决定。选型建议：参数校验失败这类"必然失败"的错误不该放进重试范围——重试一万次也不会通过。

**长对话摘要**：`SummarizationMiddleware`，达到 `trigger` 阈值（按消息数/token数/占比）后，把旧消息压缩成摘要，只保留最近 `keep` 指定的原文量。默认摘要容易漏掉"用户明确不要什么"（否定约束），需要自定义 `summary_prompt` 显式要求保留。

**清理旧工具结果**：`ContextEditingMiddleware` + `ClearToolUsesEdit`，处理的是 `SummarizationMiddleware` 管不到的"工具返回值膨胀"问题——旧的工具结果超过 `trigger` token 数后被替换成占位符，只保留最近 `keep` 次的完整结果。两者的分工：

| 维度 | SummarizationMiddleware | ContextEditingMiddleware |
| --- | --- | --- |
| 处理对象 | 对话消息（Human + AI） | 工具调用结果（ToolMessage） |
| 处理方式 | 压缩成摘要文本 | 替换为占位符 |

### 7. 自定义 Middleware：装饰器 vs 类

**装饰器模式**（`@before_model`/`@after_model`/`@wrap_model_call`/`@wrap_tool_call`）：轻量，适合"写一次、一个场景用"的一次性逻辑。

**类模式**（继承 `AgentMiddleware`，重写同名方法）：适合需要参数化配置、要在多个 Agent 间复用的治理规则——比如"不同角色的用户有不同的导出行数上限"这种带状态、带初始化参数的逻辑。

```python
class ExportGovernanceMiddleware(AgentMiddleware):
    def __init__(self, role_limits: dict = None):
        super().__init__()
        self.role_limits = role_limits or {"default": 100_000}

    def wrap_tool_call(self, request, handler):
        ...   # 用 self.role_limits 做业务判断
```

### 8. 动态 Prompt：让同一个 Agent 适配不同场景

`@dynamic_prompt` 根据每次请求的实际内容（用户消息、`runtime.context`）**动态生成** System Prompt，替代"一个又大又全的静态 Prompt 塞满所有分支规则"。适用场景是"同一个 Agent 处理多种任务风格"；不适用场景是审计日志/重试/拦截这类，那些各自有专门的钩子。**顺序上，`@dynamic_prompt` 通常放在 Middleware 列表最后**，因为它会覆盖最终生效的 System Prompt。

### 9. Middleware 顺序很重要

课件给出的"生产级栈"示例把顺序分了层：安全层（脱敏、HITL）最先 → 可靠性层（重试、降级）→ 限流层 → 上下文治理层 → 自定义业务规则 → 动态 Prompt 最后。这不是随意排列——脱敏必须在最前面，否则后面所有环节都可能已经处理过未脱敏的原始数据；动态 Prompt 必须在最后，否则会被后面的 Middleware 覆盖掉。**调换顺序可能导致行为不一致，这是本章唯一反复强调"必须验证"的点。**

---

## 三、课件勘误与更新

### 已确认

**1）`from langgraph_core.messages import ToolMessage` —— 错误（拼写/包名有误）**

- 课件原文（1.3.1 节代码块）：`from langgraph_core.messages import ToolMessage`。
- 问题类型：**错误**。不存在名为 `langgraph_core` 的包。课件其余所有位置（包括同一份课件、以及 08、09 两份课件）统一使用的都是 `from langchain_core.messages import ToolMessage`，这里属于内部不一致的笔误。
- 正确写法：`from langchain_core.messages import ToolMessage`。
- 来源：与课件自身其余代码块交叉核对一致；`langchain_core` 是 LangChain 生态的标准基础包，`ToolMessage` 定义在其 `messages` 模块下（该导入路径已在 08、09 篇课件的多处代码中被验证使用）。

**2）`from langgraph.agents.middleware import ToolRetryMiddleware` —— 错误（包路径有误）**

- 课件原文（3.1 节代码块）：`from langgraph.agents.middleware import ToolRetryMiddleware`。
- 问题类型：**错误**。`agents.middleware` 这套体系在 `langchain` 包下，不在 `langgraph` 包下——课件其余所有 Middleware 导入（`ModelCallLimitMiddleware`、`HumanInTheLoopMiddleware`、`PIIMiddleware`、`ModelRetryMiddleware`、`ModelFallbackMiddleware`、`SummarizationMiddleware`、`ContextEditingMiddleware` 等）都正确写的是 `from langchain.agents.middleware import ...`，唯独这一处写成了 `langgraph.agents.middleware`。
- 正确写法：`from langchain.agents.middleware import ToolRetryMiddleware`。
- 来源：https://reference.langchain.com/python/langchain/agents/middleware/tool_retry/ToolRetryMiddleware （官方参考文档确认 `ToolRetryMiddleware`、`ModelRetryMiddleware`、`ModelFallbackMiddleware` 均在 `langchain.agents.middleware` 下）

**3）`ModelRetryMiddleware` / `ToolRetryMiddleware` / `ModelFallbackMiddleware` 均为真实存在的内置 Middleware —— 课件用法正确**

- 核实这三个类确实存在，可从 `langchain.agents.middleware` 导入，构造参数（`max_retries`、`retry_on`、`on_failure`、备用模型位置参数）与课件示例的写法一致，未发现错误，此处作为"确认无误"记录，避免学员因上一条勘误误以为整个重试机制都是虚构的。
- 来源：https://reference.langchain.com/python/langchain/agents/middleware/model_retry/ModelRetryMiddleware ；https://reference.langchain.com/python/langchain/agents/middleware/tool_retry/ToolRetryMiddleware

**4）`SummarizationMiddleware(trigger=..., keep=...)` —— 课件用的是当前推荐写法，未过时**

- 课件原文（3.2 节）：`SummarizationMiddleware(model=..., trigger=("messages", 8), keep=("messages", 4), summary_prompt=...)`。
- 说明：官方文档里存在更老的参数名 `max_tokens_before_summary` / `messages_to_keep`，这两个**已标记弃用**，官方现在推荐的正是课件使用的 `trigger` / `keep` 元组写法（支持 `("messages", N)` / `("tokens", N)` / `("fraction", 0.x)` 三种维度）。此处课件是准确的、面向未来的写法，特此确认，避免学员误以为这是旧写法。
- 来源：https://reference.langchain.com/python/langchain/agents/middleware/summarization/SummarizationMiddleware

**5）`model="deepseek-v4-flash"` —— 课件用的是当前有效模型名**

- 课件全篇统一使用 `deepseek-v4-flash`（通过 `init_chat_model(..., model_provider="openai", base_url="https://api.deepseek.com")` 接入）。经核实，这是 DeepSeek 当前（2026-04-24 V4 发布后）的正式模型名，与 09 篇课件里已过时的 `deepseek-chat` 形成对比——本篇课件在模型命名上反而是准确、最新的，特此确认。
- 来源：https://api-docs.deepseek.com/updates/

### 待核实

- `HumanInTheLoopMiddleware` 的 `interrupt_on` 精确配置形态（`{"工具名": False}` 表示不中断、`{"工具名": {"allowed_decisions": [...]}}` 表示中断并限定审批选项）——课件示例的写法符合公开博客/文档里常见的用法模式，但未能通过官方 reference 页面逐字段核对，建议实操前对照 `HumanInTheLoopMiddleware` 的官方 API 文档确认字段名。
- `PIIMiddleware` 自定义 `detector` 传入正则字符串时，`hash`/`mask` 两种策略是否存在已知 bug（社区有 issue 报告自定义检测函数在 `hash`/`mask` 策略下可能抛 `KeyError: 'value'`，但传入正则字符串这种课件的用法方式是否受影响未验证）——建议实操时如遇到该报错，检查是否为已知问题。
- `ContextEditingMiddleware` / `ClearToolUsesEdit` 里 `clear_tool_inputs`、`token_count_method` 等参数在不同版本间是否有变动，未逐版本核实。

---

## 四、课件没讲透的关键点补充

**1）Middleware 的执行顺序不是"从上到下"这么简单**

课件展示了 `before_agent → before_model → wrap_model_call → LLM → after_model → wrap_tool_call → Tool → after_agent` 这个"一次通过"的流程图，但实际上一个 Agent 循环里模型可能被调用很多轮（09 篇讲的 ReAct 循环）。真实的执行顺序是：

```
before_agent（只在整个 Agent 启动时跑一次）
  → [ 循环: before_model → wrap_model_call → after_model
      → (如果有 tool_calls) wrap_tool_call → 循环回 before_model ]
  → after_agent（只在整个 Agent 结束时跑一次）
```

也就是说 `before_model`/`wrap_model_call`/`after_model`/`wrap_tool_call` 这四个钩子在一次 `invoke()` 里可能各触发 N 次（N = ReAct 循环轮数），而 `before_agent`/`after_agent` 只触发一次。`ModelCallLimitMiddleware` 正是靠在 `before_model` 里做计数、判断是否超限来实现限流的——理解了"循环触发"这一点，才能明白它为什么能拦住死循环。

**2）多个同类型 Middleware 的组合顺序会影响实际行为**

课件在"生产级 Middleware 栈"里提到"顺序很重要"，但没具体展开**同一个钩子被多个 Middleware 占用时的执行次序**。以 `wrap_tool_call` 为例，如果同时注册了 `PIIMiddleware`（脱敏）和 `ExportGovernanceMiddleware`（业务拦截），两者按 `middleware=[...]` 列表顺序**像洋葱一样嵌套包裹**——排在前面的先接触到最原始的 `request`，也最后拿到 `handler` 返回的结果。这和 Web 框架（如 Express/Koa）中间件洋葱模型是同一个心智模型，课件没有明说这个类比，但理解它能帮你推断任意组合的执行顺序。

**3）HITL 中断与 09 篇 `interrupt_before` 的关系**

课件把 `HumanInTheLoopMiddleware` 作为一个"开箱即用"的能力介绍，没有说明它与 09 篇手写的 `interrupt_before=["tools"]` 是不是一回事。合理的理解是：`HumanInTheLoopMiddleware` 是在更细的粒度上（按单个工具名配置，而不是按节点名）做的封装，底层同样依赖 checkpointer 做状态持久化与恢复，产生的暂停效果对使用者来说类似，但配置方式从"手写节点/断点"变成了"声明式列表"。

**4）`exit_behavior="continue"` 为什么只在 `ToolCallLimitMiddleware` 里有意义**

`ModelCallLimitMiddleware` 没有 `"continue"` 选项（只有 `"end"`/`"error"`），因为模型调用达到上限后已经没有"模型"可以继续生成解释性文字了；而工具调用达到上限时，模型本身还能继续被调用一次，去"消化"这条限流信息、组织语言回复用户——这是两个 Middleware 可选项不对称的底层原因，课件的表格列出了区别但没解释为什么。

---

## 五、Python 随堂补基础

**① 装饰器 `@xxx` —— "包一层"的语法糖**
```python
def before_model(func):          # 装饰器本质是"接收函数、返回新函数"
    def wrapper(state, runtime):
        print("调用前")
        return func(state, runtime)
    return wrapper

@before_model
def log_before_model(state, runtime):
    ...
# 等价于：log_before_model = before_model(log_before_model)
```
LangChain 的 `@before_model`/`@wrap_tool_call` 比这个示例复杂（还处理了钩子注册、state_schema），但语法本质是一样的：装饰器把普通函数"包装"成框架认识的 Middleware 对象。

**② 类继承 + 方法重写 —— 类模式 Middleware 的语法基础**
```python
class AgentMiddleware:
    def before_model(self, state, runtime): return None   # 基类默认什么都不做
    def wrap_tool_call(self, request, handler): return handler(request)

class MyMiddleware(AgentMiddleware):
    def wrap_tool_call(self, request, handler):   # 重写父类方法
        print("拦截了一次工具调用")
        return handler(request)
```

**③ 闭包 + `global` —— 跨调用保存状态（09/10 篇的重试计数器）**
```python
local_failures = 0   # 模块级变量

def retry_local_then_cloud(request, handler):
    global local_failures      # 声明要修改的是外层变量，不是新建局部变量
    local_failures += 1
    ...
```
`global` 是必须的：不写的话，函数内部 `local_failures += 1` 会被当成"新建一个局部变量"，报 `UnboundLocalError`。

**④ `NotRequired[int]` —— TypedDict 里"可以不传"的字段**
```python
from typing_extensions import NotRequired, TypedDict
class ExportAgentState(TypedDict):
    model_call_count: NotRequired[int]   # 可以不传这个键，缺省时代码里自己处理默认值
```

**⑤ `try/except` 捕获特定异常 —— block 策略的用法基础**
```python
from langchain.agents.middleware import PIIDetectionError
try:
    result = agent.invoke({...})
except PIIDetectionError as e:
    print(f"检测到敏感信息：{e.matched_entities}")   # e 是异常对象，携带额外信息
```

---

## 六、自测清单

**是什么**
1. LangGraph/LangChain Middleware 的六大钩子分别是什么？
2. `before_model` 和 `wrap_model_call` 的函数签名分别是什么样的？
3. `request` 和 `handler` 分别代表什么？
4. `state` 和 `runtime` 分别管的是什么范畴的信息？
5. PIIMiddleware 的四种脱敏策略是什么，各自的效果差异是什么？

**为什么**
6. 为什么"决定要不要发生这次调用"的逻辑必须写在 `wrap_*` 里，不能写在 `before_*`/`after_*` 里？
7. 为什么 `runtime.context` 不会自动影响模型的回答？要让它生效需要做什么？
8. 为什么 `thread_limit` 必须配合 `checkpointer` 使用？
9. 为什么 `ModelCallLimitMiddleware` 没有 `exit_behavior="continue"` 选项，而 `ToolCallLimitMiddleware` 有？
10. 为什么"生产级 Middleware 栈"里脱敏要放最前面、动态 Prompt 要放最后面？
11. 为什么重试逻辑要写在 Middleware 里，而不是写进工具函数内部？

**什么时候用**
12. 什么时候该用装饰器模式，什么时候该用类模式自定义 Middleware？
13. 什么场景该用 `SummarizationMiddleware`，什么场景该用 `ContextEditingMiddleware`？
14. 什么样的操作应该配 `HumanInTheLoopMiddleware`（HITL），什么样的不需要？
15. 什么时候该用 `redact`，什么时候该用 `block`？

---

## 七、动手小练习

**练习 A（20 分钟）：写一个耗时统计 Middleware**
用 `@wrap_tool_call` 写一个 Middleware：记录每次工具调用的耗时（`time.time()` 前后各打点），如果某次调用超过 2 秒，额外打印一条警告日志。挂到任意一个带工具的 `create_agent` 上验证效果。
> 目标：吃透 `handler(request)` 前后能插入代码这件事，以及"不调 handler 工具就不执行"的规则。

**练习 B（30 分钟）：组合两个安全 Middleware**
给报表导出 Agent（可以直接沿用课件的 `check_export_permission` + `create_export_task` 两个工具）同时挂上 `PIIMiddleware("email", strategy="redact", apply_to_input=True)` 和一个自定义的 `@wrap_tool_call` 拦截器（超过 10 万行的导出直接拦截，返回伪造 `ToolMessage`）。用一条消息（带一个假邮箱 + 一个超大 `estimated_rows`）触发 Agent，验证：① 模型看到的是脱敏后的邮箱；② 导出请求被拦截、模型能读到拦截原因并组织语言回复用户。
> 目标：体会课件强调的"Middleware 顺序"——试着把两个 Middleware 顺序调换，观察脱敏是否还生效于工具拦截器能看到的 `request.state`。
