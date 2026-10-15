# Multi-Agent 编排 复习笔记
> 对应课件：6.Multi Agent 编排/1.Multi-Agent 架构：从单兵作战到团队协作.md

## 一、在知识体系中的位置

- **前置依赖**
  - **LangChain / LangGraph**：Multi-Agent 系统本质就是一张 **LangGraph 状态图**（Graph/Node/Edge），本讲代码全部基于 `langgraph`、`langgraph-supervisor`。不懂 LangGraph 的状态/节点/边，就看不懂编排。
  - **RAG**：每个 Worker Agent 内部往往就是一个 RAG Agent（研究 Agent 配搜索工具做检索）。Multi-Agent 是在 RAG/单 Agent 之上的"团队层"。
  - **Agent 记忆系统（上一讲）**：多 Agent 协作时"谁能读写哪块记忆""handoff 时传递哪些上下文"，直接复用上一讲的作用域/治理概念。
- **后续用途**
  - **A2A（Agent-to-Agent）**：本讲讲的是**同一进程内**的多 Agent 编排；A2A 解决的是**跨服务/跨团队/跨平台**的 Agent 互通（能力发现、任务委派）。本讲第 7.8 节是 A2A 的引子。
  - **MCP**：标准化"Agent↔工具/资源"的连接，让工具能被不同 Agent 复用。
  - **Agentic RAG**：把"检索"本身做成一个可被 Supervisor 调度的专家 Agent。

一句话定位：**Multi-Agent = 把"单一职责原则"和"关注点分离"从软件工程搬到 Agent 架构**，用多个专注的小 Agent 替代一个什么都干的大 Agent。

## 二、核心知识点精讲

### 1. 为什么需要多 Agent：单 Agent 的三个结构性局限

这是本讲的"为什么"，必须讲透：

**局限一：工具越多，选择错误率越高。**
模型要在更大的候选工具集里判断"用哪个、传什么参数"。候选越多，选错、传错参、无效调用的概率越高——类似决策理论的**选择过载效应**（choice overload）。
注意课件的严谨表述：**"10 个工具"不是普适阈值**，实际拐点取决于模型能力、工具描述质量、参数设计、任务类型。所以拆分边界要**靠评测确定**，不能机械按数字拆。

**局限二：上下文堆积，关键信息被淹没。**
单 Agent 的对话历史随轮次膨胀。一次 web_search 返回可能 1500-3000 token，几轮下来核心指令就被工具返回的噪音淹没。128K 窗口看着大，但不做上下文管理，多轮 tool call 很快吃满，模型"忘了最初要干什么"。

**局限三：推理路径黑箱，难以调试。**
单 Agent 输入请求、输出结果，中间过程混在一个流程里。出错时无法定位是工具层、推理层还是执行层的问题，只能靠最终输出逆向猜。多 Agent 每个有独立日志，可逐层定位。

**三者的共同根源都是"一个上下文窗口承担了太多职责"。** 多 Agent 的解法本质是**上下文隔离**——把不同职责拆到不同 Agent，各自维护自己干净的上下文。（这一点课件点到但没展开，见第四节补充。）

### 2. Supervisor 模式：总控 + 专家

**核心思想：职责分离。** 专家 Agent 专注执行子任务，Supervisor 专注任务分发与结果整合。
类比餐厅：Supervisor = 前台经理（接单、派活、整合出品），Worker = 厨师（只管做菜，不管订单来源和上菜时序）。

**Supervisor 三大职责：** 拆解任务（理解意图、分解子任务）｜路由调度（叫哪个 Agent、什么顺序）｜整合输出（把各结果拼成最终答案）。

**Worker 的专注：** 只关心完成分配的子任务，不关注其他 Agent 状态、任务来源、结果如何组合，完成即返回、不留多余状态。这是**单一职责原则**在 Agent 架构的落地。
课件的重要修正：Worker "不拥有全局编排状态" ≠ "运行时完全不保留消息历史"——图运行时仍可能按配置把 Worker 的消息带回 Supervisor（这正是 `output_mode` 参数控制的事）。

### 3. 编排的本质：Graph / Node / Edge / Handoff

Multi-Agent 系统本质是**状态图**，不是多个 prompt 的排列：

- **Graph**：完整执行流程 + 共享状态。
- **Node**：一个 Agent、工具调用、校验器或人工审批步骤。
- **Edge**：节点间的转移条件，可固定顺序，也可由模型按结果动态选择。
- **Handoff（交接）**：把**控制权**和**必要上下文**从一个 Agent 转交给另一个。

**必须区分的两件事（本讲精髓）：**
1. **控制权转移**：下一步由哪个 Agent 执行。
2. **消息传递**：下一个 Agent 能看到哪些用户消息、工具结果、前序输出。

> 只设计了路由、没定义消息传递范围 → Worker 拿不到必要事实；把全部历史无差别传递 → 又重新引入上下文膨胀。**这就是多 Agent 最微妙的成本平衡点。**

### 4. 代码实战：LangGraph 搭 Supervisor（关键 API 精讲）

三步走：建研究 Agent → 建数学 Agent → 交给 Supervisor 调度。

**建 Worker：`create_agent`（LangChain 1.0 的新工厂函数）**

```python
from langchain.agents import create_agent   # 1.0 新 API，取代旧的 create_react_agent

research_agent = create_agent(
    model=model,
    tools=[web_search],
    system_prompt="你是研究代理。仅协助研究，禁止执行数学任务……",  # 注意：Worker 用 system_prompt
    name="research_agent",
)
```

`create_agent` 返回一个已编译的 LangGraph，可以直接 `.stream(inputs, stream_mode="values")` 单独测试——这是"每个 Worker 可单独测试"原则的落地。

**建 Supervisor：`create_supervisor`**

```python
from langgraph_supervisor import create_supervisor

supervisor = create_supervisor(
    model=model,
    agents=[research_agent, math_agent],
    prompt="你是管理两个代理的监督者……",   # 注意：Supervisor 用 prompt（不是 system_prompt！见勘误）
    add_handoff_back_messages=True,
    parallel_tool_calls=False,               # 一次只交接一个 Worker
    output_mode="full_history",              # 教学时看完整链路；默认是 last_message
)
graph = supervisor.compile()
```

**运行复合任务**：`graph.stream(inputs, stream_mode="values")`。Supervisor 会自动拆解"查 GDP + 算百分比"为两步，先路由给 research_agent，再路由给 math_agent，最后整合。

### 5. Supervisor 的优缺点（选型必背）

| 优点 | 缺点 |
| --- | --- |
| 职责清晰（prompt 简洁、工具少、准确率高） | 延迟增加（每次路由是一次额外 LLM 调用，多一跳） |
| 易调试（先看路由日志，再看 Agent 日志，逐层定位） | Supervisor 成瓶颈（它出错则全局出错） |
| 可扩展（加 Agent 只需 tools+prompt，Supervisor prompt 加一行） | 不擅长并行（标准 Supervisor 串行调度） |
| 上下文隔离（各 Agent 独立历史，不互相干扰） | 成本叠加（至少 N+1 次调用，实际因内部多轮 tool call 往往数倍） |

### 6. 五种进阶模式与取舍

| 模式 | 结构 | 适用 | 关键取舍 |
| --- | --- | --- | --- |
| **层级 Supervisor** | CEO→总监→一线 | 大型项目、子任务还要再拆 | 更清晰但更多跳数、更高成本 |
| **Pipeline 管道** | A→B→C 固定顺序 | 流程固定的线性任务 | 确定性高但不灵活 |
| **对抗 Debate** | 正方⟷反方→裁判 | 需多角度论证的决策 | 减少偏见但成本翻倍 |
| **群聊 Group Chat** | 多 Agent 自由讨论+主持人 | 创意发散、头脑风暴 | 输出多样但难收敛 |
| **Swarm 去中心化** | Agent 之间直接 handoff，无中央 Supervisor | 路径难预定、用户在专家间来回切换 | 无 Supervisor 瓶颈，但易循环、上下文丢失、责任不清 |

**Swarm vs 群聊的区别（易混）**：群聊由 Moderator 统一协调；Swarm 允许当前 Agent 根据任务状态**直接**把控制权交给另一个 Agent，没有持续负责所有路由的中央 Supervisor。LangGraph 生态用 `langgraph-swarm`（`create_swarm` + `create_handoff_tool` + `default_active_agent`）实现。

**选型决策优先级（课件核心态度）：**
1. Supervisor 能解决就不上层级架构；
2. 串行够用就不引入并行；
3. **从最简单起步，验证可行再演进，避免过早复杂化。**

### 7. 生产落地要点

- **System Prompt 三要素**：你是谁（角色）｜你能做什么（职责边界）｜你不能做什么（硬约束）。
- **最小化工具集**：只暴露完成职责必需的工具。"3-5 个"是经验起点不是硬规则；工具少但职责混乱同样出错。最终靠成功率/无效调用率/延迟/成本评测边界。
- **错误处理**：LangChain `create_agent` 公开参数里**没有** `max_iterations`；图的循环上限用运行时 `recursion_limit` 设，超限抛 `GraphRecursionError`。`recursion_limit` 限制的是整张图的递归步数，不等于某个 Agent 的精确工具调用次数。工具异常应返回**结构化、可行动**的错误，区分可重试/不可重试，别盲目重试。
- **可观测性**：生产必须加 trace（课件用 LangSmith）。
- **消息历史与 handoff**：`output_mode="last_message"`（只传最后输出，省 token）vs `"full_history"`（传完整历史，便于审计但涨成本）；`add_handoff_messages` / `add_handoff_back_messages` 记录控制权转移；还应约定 Worker 返回的最小契约（`status/summary/evidence/errors/next_action`），别把网页全文/调试日志无条件回传。`create_forward_message_tool` 可让 Supervisor 直接转发 Worker 的最后消息给用户，省一次二次总结。
- **三类生产风险**：系统设计缺陷（路由循环、权限过宽）｜协作失调（重复工作、handoff 丢上下文）｜任务验证失效（结果无来源、单位错、无验收）。至少要为成功率、路由准确率、无效工具调用率、循环次数、延迟、token 成本、人工接管率建评测指标。
- **MCP / A2A 扩展**：MCP 标准化"Agent↔工具/资源"连接；A2A 面向"跨服务的 Agent↔Agent"通信（能力发现、任务委派、结果回传）。二者解决**互操作**，不自动解决任务拆解、路由正确性、上下文控制或结果验证。

## 三、课件勘误与更新

总体：这版课件对"工具数量阈值""GDP 数值"等易过期内容都加了免责声明，写作纪律好。核实后发现两处代码级问题：

**1. `create_supervisor` 的参数名错误：应是 `prompt` 而非 `system_prompt`**

- 课件原文（3.4 节）：
  ```python
  supervisor = create_supervisor(
      model=model,
      agents=[research_agent, math_agent],
      system_prompt=("你是一个管理两个代理的监督者：……"),
      ...
  )
  ```
- 问题类型：**错误**（直接照抄会抛 `TypeError: create_supervisor() got an unexpected keyword argument 'system_prompt'`）
- 正确说法：`langgraph-supervisor` 的 `create_supervisor()` 用的参数名是 **`prompt`**，不是 `system_prompt`。注意区分：**Worker 的 `create_agent()` 用 `system_prompt`**（课件 3.2/3.3 节写对了），**Supervisor 的 `create_supervisor()` 用 `prompt`**——课件在这里把两者搞混了。官方签名：`create_supervisor(agents, *, model, tools=None, prompt=None, ..., output_mode="last_message", add_handoff_messages=True, ...)`。
- 来源：https://reference.langchain.com/python/langgraph-supervisor/supervisor/create_supervisor ｜ https://github.com/langchain-ai/langgraph-supervisor-py

**2. `TavilySearchResults` 已废弃，应改用 `langchain_tavily.TavilySearch`**

- 课件原文（3.1/3.2 节）：
  ```python
  pip install -U tavily-python langchain-community langchain-openai langgraph-supervisor
  from langchain_community.tools.tavily_search import TavilySearchResults
  web_search = TavilySearchResults(max_results=3)
  ```
- 问题类型：**已过时**
- 正确/最新说法：`langchain_community` 里的 `TavilySearchResults` 自 LangChain **0.3.25 起废弃，并计划在 1.0 移除**。官方要求迁移到独立包：`pip install -U langchain-tavily`，然后 `from langchain_tavily import TavilySearch; web_search = TavilySearch(max_results=3)`。这一点尤其要注意——课件其他地方已经用了 LangChain 1.0 的新 `create_agent`，却仍配旧的 `TavilySearchResults`，属于新旧 API 混用，在 1.0 环境下会因该类被移除而报错。
- 来源：https://docs.langchain.com/oss/python/integrations/tools/tavily_search ｜ https://reference.langchain.com/python/langchain-tavily/tavily_search/TavilySearch

**3. GDP 示例数值与 2024 真实值偏差较大（课件已免责，此处补充事实供参考）**

- 课件原文（3.5 节）："美国 GDP: 28.18 万亿美元，纽约州 GDP: 1.671 万亿美元 → 纽约州占 5.93%"，并注明"以上数值是来源文章示例运行时的输出……不应当作为固定事实"。
- 问题类型：**不严谨（课件已用免责声明对冲）**
- 正确/最新说法：按 BEA 官方数据，2024 全年美国名义 GDP 约 **29.18–29.3 万亿美元**，纽约州 GSP 约 **2.32 万亿美元**，真实占比约 **8%**，而非课件示例的 5.93%（其纽约州数值 1.671 万亿明显偏低）。这恰好印证课件自己的观点：生产系统必须要求研究 Agent 返回**来源、发布日期和原始数值**，并由校验步骤检查单位和口径——连演示数字都可能离谱。
- 来源：https://www.bea.gov/sites/default/files/2025-03/stgdppi4q24-a2024.pdf ｜ https://en.wikipedia.org/wiki/Economy_of_New_York_(state)

**经核实无误 / 课件做得对的地方（增强信心）：**

- **`create_agent` 用法是最新的**：`from langchain.agents import create_agent` + `system_prompt=` 是 LangChain 1.0 的官方新工厂函数，取代了旧的 `from langgraph.prebuilt import create_react_agent`。课件在这里领先于很多还在用 `create_react_agent` 的旧教程。（小提示：曾有社区反馈 v1.1.0 短暂出现 `create_agent` 导入问题，遇到导入报错时核对已装版本即可。）https://reference.langchain.com/python/langchain/agents/factory/create_agent
- **`output_mode` 默认值正确**：课件说 `create_supervisor` 默认是 `last_message`、示例显式选 `full_history`——与官方签名（`output_mode: OutputMode = "last_message"`）完全一致。
- **`recursion_limit` / `GraphRecursionError` / 无 `max_iterations`**：均属实，`create_agent` 确无 `max_iterations` 公开参数，循环上限走运行时 `recursion_limit`。
- **`langgraph-swarm` 骨架正确**：`create_swarm([...], default_active_agent=...)` + `create_handoff_tool(agent_name=..., description=...)` 与官方 API 一致。https://github.com/langchain-ai/langgraph-swarm-py
- **MCP / A2A 定位准确**：A2A 由 Google 于 2025-04 发布、2025-06 移交 Linux Foundation 治理，核心是通过 Agent Card 做能力发现 + 任务委派（Agent↔Agent）；MCP 面向 Agent↔工具/资源连接。课件"MCP 连工具、A2A 连 Agent，二者只解决互操作不解决编排正确性"的说法准确。https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/ ｜ https://en.wikipedia.org/wiki/Agent2Agent
- **`create_forward_message_tool` 真实存在**：课件"用 `forward_message` 一类转发工具直接把 Worker 最后消息转发给用户"的说法属实，返回 `Command(goto="__end__")` 终止图、省一次 Supervisor 总结。

### 待核实

1. **实战项目仓库** `git.miaoatech.cn/zeroleap/Multi-Agent.git`：私有/内网地址，无法公开核实其代码与课件是否一致，以学员本地实际代码为准。
2. **`add_handoff_back_messages` 的默认值**：官方签名显示为 `add_handoff_back_messages: Optional[bool] = None`（内部再决定默认行为），课件示例显式传 `True`。是否与你安装版本的默认行为一致，需按已装 `langgraph-supervisor` 版本核对。
3. **各 Token 消耗数字**（"web_search 返回 ~1500-3000 tokens""5 轮后可达 15K"）：为量级示意，随模型、工具、内容长度变化，不必当精确值。

## 四、课件没讲透的关键点补充

**1. 为什么拆多 Agent 的根本原因是"上下文隔离"（课件三个局限背后的统一解释）**

三个局限（工具选择、上下文淹没、黑箱调试）看似独立，根子是**同一个**：一个上下文窗口塞进了太多职责。多 Agent 的核心价值不是"人多力量大"，而是**给每个职责一块干净、聚焦、可控的上下文**：

- 研究 Agent 的窗口里只有"搜索任务 + 搜索结果"，不掺杂计算逻辑 → 工具选择空间小、准确率高；
- 数学 Agent 的窗口里只有"数字 + 计算工具"，不掺杂几千 token 的网页 → 关键信息不被淹没；
- 每个 Agent 独立日志 → 出错时知道是哪块窗口出的问题。

所以"要不要拆多 Agent"的判断标准，其实是"**单个上下文窗口是否已经承担了过多、互相干扰的职责**"。这也解释了为什么 Anthropic 的 Context Engineering 把"用子 Agent 返回精简摘要"列为上下文管理手段之一——多 Agent 本身就是一种上下文工程。

**2. Supervisor / Pipeline / Swarm 的取舍，本质是"路由由谁决定"**

- **Pipeline**：路由**写死在代码里**（A→B→C）。确定性最高、成本最低、最好调试，但一步都不能变。适合流程固定的任务。
- **Supervisor**：路由**由 Supervisor 这个模型每步决定**。灵活性中等，但每次路由 = 一次 LLM 调用（延迟/成本的来源），且 Supervisor 是单点。适合大部分"子任务不固定"的场景。
- **Swarm**：路由**分散到每个 Agent**，谁都能决定下一步交给谁。最灵活，无中央瓶颈，但**最容易失控**——循环、上下文丢失、责任不清。

课件的决策优先级"从简单起步"翻译过来就是：**能写死路由（Pipeline）就别让模型决策（Supervisor），能中心化决策（Supervisor）就别去中心化（Swarm）**。每增加一层动态性，都要用循环上限、可交接目标白名单、返回条件来兜底。

**3. Agent 间上下文传递的代价（本讲最容易被跳过、却最影响成本的点）**

课件反复强调"控制权转移 ≠ 消息传递"，但没算清代价账。展开：

- **传太少**（只传 `last_message`）：Worker B 可能拿不到 Worker A 的关键中间事实，导致重复劳动或结论断裂。
- **传太多**（传 `full_history`）：把 A 的完整搜索历史、调试日志全灌给 B，**多 Agent 好不容易省下的上下文又被 handoff 重新塞满了**——等于白拆。
- **正确姿势**：定义 Worker 返回的**最小契约**（`status/summary/evidence/next_action`），只传结构化的关键事实。研究 Agent 交给数学 Agent 的应该是"美国 GDP=X，纽约=Y"这两个数，而不是整页搜索结果。

一句话：**多 Agent 省下的上下文，可能在 handoff 环节又花回去。** 编排设计的一半功夫花在"每次交接到底传什么"上。

**4. 为什么标准 Supervisor "不擅长并行"（课件列为缺点但没说原理）**

标准 Supervisor 是**串行**的：它调用 Worker A → 等 A 返回 → 观察结果 → 再决定调 B。因为它的下一步路由**依赖上一步的结果**（"研究 Agent 查到 GDP 后，我才知道要让数学 Agent 算什么"）。要真并行（同时跑多个互不依赖的子任务），需要额外设计——`parallel_tool_calls=True`（且要求模型提供商支持）、并发状态写入的冲突处理、结果合并逻辑。所以课件说"多任务并行需要额外设计"，不是随便说说。

**5. 成本的真实量级：为什么是"N+1 的数倍"**

课件说"至少 N+1 次 LLM 调用"，但补了一句"实际往往数倍"。为什么？因为每个 Worker Agent **内部**是一个 ReAct 循环：它可能"思考→调工具→看结果→再思考→再调工具→……"好几轮，**每一轮都是一次 LLM 调用**。所以 3 个 Agent 的任务，真实调用数可能是十几次甚至几十次。这就是为什么可观测性（trace）和 `recursion_limit`（防失控循环烧钱）在生产里是刚需，不是可选项。

## 五、Python 随堂补基础

本讲代码用到的语法点：

**1. `os.environ`：设置环境变量（放 API Key）**

```python
import os
os.environ["TAVILY_API_KEY"] = "tvly-xxx"   # 等号左边是变量名字符串，右边是值
print(os.environ.get("TAVILY_API_KEY"))     # 读取用 .get，缺失时返回 None 不报错
```

**2. `@tool` 装饰器：把普通函数变成 Agent 能调的工具**

```python
from langchain_core.tools import tool

@tool
def add(a: float, b: float):
    """加法：将两个数字相加。"""   # 这段 docstring 会被模型读到，用来判断何时调用！
    return a + b
```
关键：**类型注解（`a: float`）和 docstring 都是给模型看的**——模型靠它们决定"这个工具能干嘛、参数怎么填"。写得含糊，模型就调错。

**3. 关键字参数（keyword arguments）：`name=`、`model=` 这种传参**

```python
def create(model, tools, name):
    ...
# 两种传法：
create(m, t, "agent1")                     # 位置参数：靠顺序
create(name="agent1", model=m, tools=t)    # 关键字参数：靠名字，顺序随意、可读性高
```
本讲勘误的核心就是关键字参数名写错——`system_prompt=` vs `prompt=` 是两个不同的名字，传错就 `TypeError`。

**4. 列表里放对象：`agents=[research_agent, math_agent]`**

```python
agents = [research_agent, math_agent]   # 列表元素可以是任何对象，不只是数字/字符串
for a in agents:                        # 遍历
    print(a.name)
```

**5. 元组构造消息：`("human", "你好")`**

```python
inputs = {"messages": [("human", "什么是牛顿第二定律？")]}
# ("human", "...") 是一个二元组，(角色, 内容)，LangChain 会自动转成消息对象
```

**6. `for ... in graph.stream(...)`：流式遍历生成器**

```python
for chunk in graph.stream(inputs, stream_mode="values"):
    chunk["messages"][-1].pretty_print()   # [-1] 取列表最后一个元素
```
`stream()` 返回的是**生成器**——不是一次性算完，而是每产出一个中间状态就 `yield` 一次，所以能边跑边看过程。`[-1]` 是负数索引，表示"倒数第一个"。

**7. 字典取值：`chunk["messages"]` 和嵌套访问**

```python
state = {"messages": [msg1, msg2]}
last = state["messages"][-1]     # 先按 key 取列表，再按索引取最后一个
config = {"recursion_limit": 50} # 运行配置也是字典
```

**8. 三引号多行字符串：写长 prompt**

```python
prompt = (
    "你是研究代理。\n\n"     # 用括号 + 相邻字符串自动拼接，\n 是换行
    "指令：\n"
    "- 仅协助研究任务\n"
)
# 或用三引号：
prompt = """你是研究代理。
指令：
- 仅协助研究任务"""
```

## 六、自测清单

**是什么：**
1. 单 Agent 的三个结构性局限分别是什么？
2. Supervisor 的三大职责是什么？Worker 的"单一职责"具体指什么？
3. Graph / Node / Edge / Handoff 四个概念各指什么？
4. "控制权转移"和"消息传递"分别指什么？为什么必须分开设计？
5. `output_mode` 的 `last_message` 和 `full_history` 有什么区别？默认是哪个？

**为什么：**
6. 为什么工具越多、单 Agent 的选择错误率越高？"10 个工具"是硬阈值吗？
7. 为什么三个局限的共同根源是"上下文窗口承担了太多职责"？
8. 为什么 Supervisor 模式"不擅长并行"？串行的根本原因是什么？
9. 为什么说"多 Agent 省下的上下文，可能在 handoff 环节又花回去"？
10. 为什么 Supervisor 的真实 LLM 调用次数往往是"N+1 的数倍"？
11. 为什么 Swarm 比 Supervisor 更容易失控？要用哪些机制兜底？

**什么时候用：**
12. 任务流程完全固定（搜索→分析→出报告），选哪种模式？为什么不用 Supervisor？
13. 出现什么信号时，说明该从单 Agent 拆成多 Agent？
14. 研究 Agent 要把结果交给数学 Agent，应该传什么、不该传什么？
15. 什么时候该引入 A2A 而不是继续用本讲的进程内编排？MCP 和 A2A 分别解决什么？

## 七、动手小练习

**练习 1（约 30 分钟）：把课件的 Supervisor 例子跑通并修正勘误**

1. 用 `pip install -U langchain-tavily langchain-openai langgraph-supervisor` 安装（注意用**新**的 tavily 包）；
2. 按课件搭 research_agent（工具改用 `from langchain_tavily import TavilySearch`）和 math_agent；
3. 组装 Supervisor 时，**把课件的 `system_prompt=` 改成 `prompt=`**，验证改之前会报 `TypeError`、改之后正常；
4. 跑一个复合任务（如"查某国 2024 GDP 并算某州占比"），用 `stream_mode="values"` 观察 Supervisor 如何拆解、路由、整合。
体会点：亲手踩一遍两个勘误，比背下来记得牢；观察日志里 handoff 的发生时机。

**练习 2（约 25 分钟）：对比 last_message 与 full_history 的上下文代价**

用同一个复合任务跑两次，一次 `output_mode="last_message"`，一次 `"full_history"`：
1. 打印两种模式下最终 `state["messages"]` 的条数和总字符数；
2. 观察 `full_history` 下 Supervisor 的上下文里多了哪些 Worker 中间消息；
3. 思考：如果 Worker 内部做了 5 轮 tool call，`full_history` 会把这些全带回 Supervisor 吗？这对成本意味着什么？
体会点：亲眼看到"消息传递范围"如何直接决定上下文膨胀——理解第四节补充 3 的代价账。
