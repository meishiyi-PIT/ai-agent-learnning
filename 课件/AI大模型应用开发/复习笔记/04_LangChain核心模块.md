# LangChain 核心模块 复习笔记
> 对应课件：1.LangChain核心模块实战指南.md
> 复习环境基准：langchain 1.3.1 / langchain-community 0.4.1 / langchain-openai 1.4.x / langchain-classic 1.0.8（笔记中所有"实测"均在此环境验证，2026-07）

## 一、在知识体系中的位置

**前置依赖：**
- Python 基础：函数、类、装饰器、类型注解（本笔记第五节补）
- 大模型 API 的基本概念：什么是 prompt、什么是 token、API Key 是干嘛的
- 对"聊天补全（Chat Completions）"接口的直觉认识：发一组消息，收一条回复

**后续哪些主题会用到它（本课程后续模块）：**

| 后续模块 | 依赖本课件的哪部分 |
| :--- | :--- |
| RAG | Embedding 模型、PromptTemplate、LCEL 链、输出解析器（RAG 链就是 `检索 | prompt | llm | parser`） |
| LangGraph | Runnable 接口、消息类型（LangGraph 的节点就是 Runnable，状态里流转的就是 Message 列表；`create_agent` 底层就是 LangGraph） |
| MCP / Agent Skills | Tool 抽象与 Function Calling 消息流转（MCP 本质是"把工具的定义和执行搬到进程外"，底层协议逻辑与 6.3 节完全同构） |
| 记忆系统 | 5.x 节的短期/长期记忆是入门版，后续会升级为 LangGraph checkpointer、摘要压缩、向量记忆 |
| Multi-Agent / A2A / Agentic RAG | `create_agent` 是最小 Agent 单元，多智能体就是把多个这样的单元编排起来 |

一句话：**这份课件是整个课程的"地基"，尤其是 Function Calling（6.3-6.6）和 LCEL/Runnable（4.3），后面每个模块都会反复用到。**

## 二、核心知识点精讲

### 2.1 LangChain 到底解决什么问题（为什么需要框架）

裸调大模型 API 只能"一问一答"。真实应用需要：多轮对话（模型本身无状态）、调外部工具（模型没有实时数据和执行能力）、多步骤流水线（翻译→摘要→翻译回来）。这些逻辑每个厂商 API 细节都不同，自己写就是大量胶水代码。LangChain 的价值 = **把这些胶水代码标准化成可拼装的模块**：Models（接模型）、Prompts（管模板）、Chains（串流程）、Memory（存上下文）、Agents（自主调工具）、Output Parsers（转结构化数据）。

关键理解：LangChain 不提供任何"智能"，智能全在大模型那边。**LangChain 提供的是工程化：统一接口、组合能力、生态集成。** 所以即使 API 名字年年变（0.x → 1.0 变化很大），"模块化 + 可组合"这个思想不变。

### 2.2 三类模型接口：为什么 90% 用 Chat Model

| 类型 | 输入→输出 | 现状 |
| :--- | :--- | :--- |
| LLM（文本补全） | 字符串 → 字符串 | 历史遗留接口，新模型基本不再提供纯补全端点 |
| Chat Model | 消息列表 → 消息对象 | **主流**，多轮对话、工具调用、结构化输出都建立在它上面 |
| Embedding | 文本 → 浮点向量 | RAG 的基石，下一模块的主角 |

为什么 Chat Model 赢了？因为**消息列表这个数据结构能承载"角色"信息**（system 定规则 / user 提需求 / assistant 是历史回复 / tool 是工具结果），而工具调用、多轮记忆都必须靠角色区分才能实现。纯字符串接口表达不了这些。

接入国产模型的通用套路：**只要厂商兼容 OpenAI 协议，就用 `ChatOpenAI` 换个 `base_url` 和 `model`**。DeepSeek（`https://api.deepseek.com`）、通义千问（`https://dashscope.aliyuncs.com/compatible-mode/v1`）都是这么接的。这也是"OpenAI 协议成了事实标准"的含义：请求格式、认证方式、返回结构都照抄 OpenAI。

三种等价写法，优先记第三种：
```python
# ① 直接用 ChatOpenAI（走兼容协议）
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="deepseek-v4-flash", api_key="sk-...", base_url="https://api.deepseek.com")

# ② 厂商专用集成类（如 ChatTongyi，需要 pip install dashscope）
# ③ 官方推荐的统一入口：init_chat_model —— 换模型只改字符串，不改代码结构
from langchain.chat_models import init_chat_model
llm = init_chat_model(model="qwen-plus", model_provider="openai",
                      api_key="sk-...", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
```
另外 DeepSeek 现在有官方集成包 `langchain-deepseek`（提供 `ChatDeepSeek` 类），比裸用 ChatOpenAI 对 DeepSeek 特性（如思考模式的 reasoning_content）支持更好。

本地零成本方案：Ollama（大模型界的 Docker）。`ollama pull qwen2.5:3b` 下载，`langchain-ollama` 包里的 `OllamaLLM`（补全接口）或 `ChatOllama`（聊天接口，与线上模型行为更一致，推荐）调用。注意课件 2.3.5 用的 `qwen2.5:3b` 需要先 `ollama pull qwen2.5:3b`（前文只演示了 pull 7b/1.5b）。

### 2.3 采样参数：temperature / top_k / top_p 到底在筛什么

模型每生成一个词，实际是在整个词表上算出一个概率分布，然后**抽签**。三个参数就是控制这次抽签的：

1. **temperature 改变分布形状**：`logit / T` 后再 softmax。T 小 → 高分词优势被放大，分布变"尖"，输出稳定；T 大 → 分布变"平"，冷门词也有机会，输出多样。它不删候选词，只改概率。
2. **top_k 按名次砍**：只留概率前 K 名。是"固定数量"截断。
3. **top_p 按累积概率砍**：从高到低累加，加到 ≥ P 为止。是"动态数量"截断——分布尖时可能只留 1-2 个词，分布平时留一堆。这就是它比 top_k 聪明的地方：**截多少由分布本身决定**。
4. 剩下的候选词概率重新归一化，**按概率随机抽**（不是选最大的，这是"采样"与"贪心解码"的区别）。

课件里"晚餐吃什么"的手算例子值得自己拿计算器走一遍，走完你会彻底记住"温度调形状、top_k/top_p 砍候选"。

实用口诀：**写代码/SQL 用低温（0~0.2）+ top_p 0.8；写创意用高温（0.9+）+ top_p 0.95；top_k 和 top_p 二选一即可。**

两个重要落地注意（课件没提，详见第三、四节）：
- OpenAI 协议的 Chat 接口**没有 top_k 参数**（它是 HuggingFace 本地推理、Ollama 等引擎才有的参数），所以你用 ChatOpenAI 只能调 temperature 和 top_p；
- DeepSeek V4 默认开"思考模式"，思考模式下 temperature/top_p **被静默忽略**（见勘误第 3 条）。

### 2.4 结构化输出：with_structured_output

程序没法消费"散文"，需要 JSON。`llm.with_structured_output(Schema)` 接受三种 Schema：
- **Pydantic BaseModel**：返回带类型校验的对象，字段错了直接报错 → 生产首选；
- **TypedDict**：返回普通 dict，无运行时校验 → 轻量；
- **原生 JSON Schema dict**：跨语言通用 → 需要动态构建 Schema 时用。

为什么它比"在 prompt 里求模型输出 JSON"靠谱？因为它优先走模型的**原生结构化能力**（底层把 Schema 转成 function calling 的工具定义或 JSON mode 约束），由推理引擎在解码层面保证格式，而不是靠模型"自觉"。

### 2.5 提示模板：参数化的 prompt

- `PromptTemplate.from_template("讲一个关于{topic}的笑话")`：纯文本模板，`{}` 是占位符。
- `ChatPromptTemplate.from_messages([("system", ...), ("human", "{question}")])`：按角色组织的多消息模板，实战主力。
- `.partial(city="成都", date=get_datetime)`：预填部分变量；**传函数名（不加括号）时，每次 format 才执行取值**——适合"当前时间"这类动态值。
- `FewShotPromptTemplate(examples, example_prompt, prefix, suffix)`：把"例题"拼进 prompt。为什么有效？因为 LLM 是模式补全机器，给 3 个"黑话→翻译"的例子，它就会沿着这个模式补第 4 个，比长篇 instructions 更能约束输出格式和风格。

### 2.6 LCEL 与链：`|` 串起来的流水线

```python
chain = prompt | llm | parser
result = chain.invoke({"input": "..."})
```
执行时数据这样流转：**dict →（prompt 填充）→ 消息列表 →（llm 调用）→ AIMessage →（parser 解析）→ str/list/对象**。每一环的输出类型正好是下一环的输入类型，这就是"前一步输出自动变下一步输入"。

`RunnableParallel(joke=chain_a, poem=chain_b)`：同一输入分发给多条链**并发**执行，结果打包成 dict 返回，总耗时 ≈ 最慢那条，而不是相加。适合"一份材料，同时生成摘要+标签+标题"这类场景。

`|` 为什么能这么用？这是 Python 运算符重载 + Runnable 统一接口，是 LangChain 的灵魂，课件一笔带过，第四节详细讲。

### 2.7 记忆：LLM 天生失忆，记忆全靠"塞"

LLM 每次请求都是独立事件，它"记得你"纯粹是因为**你把历史对话原文塞回了本次请求的消息列表里**。所有记忆方案本质都是三步：请求前取历史 → 拼进 prompt（`MessagesPlaceholder(variable_name="history")` 就是历史消息的插槽）→ 请求后把新一轮对话存回去。

- 短期记忆（内存）：`ConversationBufferMemory` 全量缓存对话，`ConversationChain` 把"取→拼→存"自动化。**注意这两个类已弃用**（见勘误 5/6），理解原理即可，新代码用下面的方案。
- 长期记忆（数据库）：`RunnableWithMessageHistory(chain, get_history_fn, input_messages_key=..., history_messages_key=...)` 包装任意链；`get_history_fn` 是 `session_id → 历史存储对象` 的映射（如 `SQLChatMessageHistory` 存 MySQL/SQLite），invoke 时通过 `config={"configurable": {"session_id": "user_001"}}` 区分用户。**session_id 是多用户隔离的关键**——不同用户各有一份历史，互不串台。

全量 buffer 的隐患：对话越长，每次请求塞的历史越多 → token 费用线性上涨、最终撑爆上下文窗口。后续"记忆系统"模块讲的摘要压缩、修剪、向量化检索，都是为了解这个问题。

### 2.8 Agent 与 Function Calling（本课件最重要的部分）

**分工：大模型负责"想"（理解意图、决定调什么工具、传什么参数），工具负责"做"（真正执行），Agent 框架负责"编排"（把想和做循环起来）。**

Function Calling 六步流（务必背下来，后面 MCP、Multi-Agent 全是它的变体）：
1. 你把工具的 JSON Schema（名字、用途、参数）随消息一起发给模型；
2. 模型判断要不要用工具；
3. 要用 → 返回结构化的 `tool_calls`（工具名+参数），**而不是自然语言**；
4. **你的代码**在本地执行函数（模型没有执行能力，就像"你用计算器，算数的是计算器不是你"）；
5. 把结果包成 `ToolMessage`（带 `tool_call_id` 与请求配对）追加进消息列表，再发一次请求；
6. 模型基于工具结果生成最终回答。

LangChain 的封装层次，从底到顶：
```python
# 底层：@tool 装饰器 —— docstring + 类型注解自动生成 JSON Schema
@tool
def get_weather(location: str) -> str:
    """查询指定城市的实时天气信息"""   # ← 这是写给模型看的说明书，不是注释！
    ...

# 中层：bind_tools —— 把 Schema 挂到请求上，手动处理 tool_calls（6.6 节手动流程）
llm_with_tools = llm.bind_tools([get_weather])

# 顶层：create_agent —— 自动完成"分析→调工具→喂结果→再分析"的循环
from langchain.agents import create_agent
agent = create_agent(model=llm, tools=[get_weather, multiply], system_prompt="...")
res = agent.invoke({"messages": [{"role": "user", "content": "成都天气怎么样？"}]})
print(res["messages"][-1].content)   # 最终回答在消息列表最后一条
```
`description` 写得越清楚，模型选工具越准——它是模型决策的唯一依据。多个工具时（课件例子：get_weather + multiply），模型完全靠各工具的描述和参数 Schema 来路由。

## 三、课件勘误与更新

1. **课件原文**：`model_name="deepseek-v4-flash"` 与 `model_name="deepseek-chat"` 混用（2.1、4.4、5.2 等多处用 `deepseek-chat`）
   **问题类型**：已过时（`deepseek-chat` 部分）
   **正确/最新说法**：DeepSeek 官方已宣布 `deepseek-chat` 和 `deepseek-reasoner` 两个模型名于 2026-07-24 弃用（为兼容暂映射到 `deepseek-v4-flash` 的非思考/思考模式）。当前应统一使用 `deepseek-v4-flash`（或更强的 `deepseek-v4-pro`）。课件里 `deepseek-v4-flash` 的写法是对的，`deepseek-chat` 的写法应全部替换。
   **来源**：https://api-docs.deepseek.com/quick_start/pricing

2. **课件原文**：2.5 节参数调优示例——对 `deepseek-v4-flash` 设置 `temperature=0.1/0.9`、`top_p` 来控制输出风格
   **问题类型**：已过时（写法当时对 deepseek-chat 有效，对 V4 默认状态无效）
   **正确/最新说法**：DeepSeek V4 系列**默认开启思考（thinking）模式**，思考模式下 `temperature`、`top_p`、`presence_penalty`、`frequency_penalty` 一律**被静默忽略（不报错但不生效）**。要让这些参数生效，需先关闭思考模式：`extra_body={"thinking": {"type": "disabled"}}`（ChatOpenAI 可通过 `extra_body` 参数传入）。
   **来源**：https://api-docs.deepseek.com/guides/thinking_mode

3. **课件原文**：`model_kwargs={"top_p": 0.8}`
   **问题类型**：不严谨
   **正确/最新说法**：`top_p` 是 `ChatOpenAI` 的显式构造参数，应直接写 `ChatOpenAI(..., top_p=0.8)`。经 model_kwargs 传入实测（langchain-openai 1.4.1）会触发警告："Parameters {'top_p'} should be specified explicitly. Instead they were passed in as part of `model_kwargs` parameter."
   **来源**：https://python.langchain.com/api_reference/openai/chat_models/langchain_openai.chat_models.base.ChatOpenAI.html

4. **课件原文**（3.4 节 partial 示例）：
   ```python
   partial_prompt = prompt.partial(
       city="成都",
       year="2026",
       date=get_datetime)  # 动态获取当前日期
   )
   ```
   **问题类型**：错误（语法错误，代码无法运行）
   **正确/最新说法**：多了一个右括号。实测 `compile()` 报 `SyntaxError: unmatched ')'`。正确写法：
   ```python
   partial_prompt = prompt.partial(city="成都", year="2026", date=get_datetime)
   ```
   （`date=get_datetime` 传函数引用、format 时求值的用法本身是对的，已实测。）
   **来源**：本地运行验证；partial 用法见 https://python.langchain.com/api_reference/core/prompts/langchain_core.prompts.prompt.PromptTemplate.html

5. **课件原文**：`from langchain_classic.memory import ConversationBufferMemory`
   **问题类型**：已过时（可运行，但属弃用 API）
   **正确/最新说法**：`ConversationBufferMemory` 自 LangChain 0.3.1 起弃用，计划 2.0 移除（实测 langchain-classic 1.0.8 下实例化会打印 LangChainDeprecationWarning，提示改用 `langchain.agents.create_agent` 的记忆能力）。1.x 推荐：短期记忆用 `create_agent` + LangGraph checkpointer，或 `RunnableWithMessageHistory`。课件把它放在 langchain_classic 下讲、且 5.3 节又给了 RunnableWithMessageHistory 方案，思路是对的，学习时以 5.3 方案为准。
   **来源**：https://python.langchain.com/docs/versions/migrating_memory/

6. **课件原文**：`from langchain_classic.chains import ConversationChain`
   **问题类型**：已过时（可运行，但属弃用 API）
   **正确/最新说法**：`ConversationChain` 自 0.2.7 弃用、2.0.0 移除（实测有 DeprecationWarning），官方建议用 `RunnableWithMessageHistory` 或 `create_agent` 替代。
   **来源**：https://python.langchain.com/docs/versions/migrating_memory/

7. **课件原文**：`from langchain_classic.agents import get_all_tool_names`
   **问题类型**：已过时（可运行，但有弃用警告）
   **正确/最新说法**：实测触发 LangChainDeprecationWarning，官方指定新导入路径为 `from langchain_community.agent_toolkits.load_tools import get_all_tool_names`。
   **来源**：https://python.langchain.com/api_reference/community/agent_toolkits/langchain_community.agent_toolkits.load_tools.get_all_tool_names.html

8. **课件原文**：`SQLChatMessageHistory(session_id=..., connection_string=mysql_url, table_name=...)`
   **问题类型**：已过时（可运行，但有弃用警告）
   **正确/最新说法**：`connection_string` 参数自 LangChain 0.2.2 弃用（实测警告原文："Use connection instead"），应写 `connection=mysql_url`。
   **来源**：https://python.langchain.com/api_reference/community/chat_message_histories/langchain_community.chat_message_histories.sql.SQLChatMessageHistory.html

9. **课件原文**（6.4 节注释）：`print(get_weather.description)  # "查询指定城市的实时天气信息"`
   **问题类型**：不严谨
   **正确/最新说法**：`description` 是**完整 docstring**（含 `Args:` 段落），不只是第一行。实测输出为 `'查询指定城市的实时天气信息\n\nArgs:\n    location: 城市名称...'`。课件 6.5 节展示的 OpenAI 格式 schema 里 description 恰好也带着 Args 段，与此一致。
   **来源**：本地运行验证；工具定义机制见 https://docs.langchain.com/oss/python/langchain/tools

10. **课件原文**（2.3.5 节）：`OllamaLLM(model="qwen2.5:3b")`
    **问题类型**：不严谨（前后不一致）
    **正确/最新说法**：前文只演示了 `ollama pull qwen2.5:7b / 1.5b`，直接跑 3b 会因模型未下载而报错，需先 `ollama pull qwen2.5:3b`（该 tag 存在）。另外对话场景更推荐 `ChatOllama`（消息接口），`OllamaLLM` 是文本补全接口。
    **来源**：https://ollama.com/library/qwen2.5

**版本事实确认（不是勘误）**：课件写的 `langchain==1.3.1`、`langchain-community==0.4.1` 均真实存在（PyPI 实查，当前最新为 langchain 1.3.14 / community 0.4.2），课件整体就是按 LangChain 1.x 新体系写的（`create_agent`、`langchain_classic` 拆分），这点与 1.0（2025-10 发布）后的官方架构一致，无需担心"课件是 0.x 老写法"。1.0 变更总览：https://docs.langchain.com/oss/python/releases/langchain-v1

### 待核实
- "先 Top-K 过滤、再 Top-P 过滤"的执行顺序：与 HuggingFace transformers 的默认实现一致，但各家闭源 API（DeepSeek/OpenAI）服务端内部采样顺序未公开，无法核实是否严格如此。理解成"两道候选词过滤闸门"即可。
- DeepSeek 的 OpenAI 兼容端点是否接受 `top_k` 参数（OpenAI 官方 Chat API 无此参数；DeepSeek 文档的请求参数列表未逐项核对）。保守做法：只用 temperature + top_p。
- 课件两张架构图/流程图为外链图片（yuque CDN），未能核对图中内容。

## 四、课件没讲透的关键点补充

### 4.1 `|` 为什么能连接一切：Runnable 与 LCEL 的本质

课件说"实现了 Runnable 接口的组件都能用 `|` 串联"，但没说这是怎么做到的。两个机制：

1. **统一接口**：`Runnable` 是一个抽象基类，规定了四个核心方法——`invoke()`（单次同步）、`batch()`（批量）、`stream()`(流式)、`ainvoke()`（异步）。PromptTemplate、ChatModel、OutputParser、乃至你 `@tool` 定义的工具、`create_agent` 返回的 Agent，全都实现了它。**所以"一切皆可 invoke"**——你学会 `chain.invoke()`，就同时学会了调用模板、模型、解析器、Agent。
2. **运算符重载**：Python 里 `a | b` 会调用 `a.__or__(b)`。Runnable 重载了 `__or__`，返回一个 `RunnableSequence` 对象——它也是 Runnable，invoke 时依次执行内部每个环节，把上一环输出喂给下一环。所以 `prompt | llm | parser` 不是"立即执行"，而是**先组装出一条可复用的流水线对象**，invoke 时才真正跑。

理解这一点后，"chain.invoke 背后发生了什么"就清晰了：
```
chain.invoke({"concept": "量子计算"})
  → prompt.invoke(dict)   得到 ChatPromptValue（消息列表）
  → llm.invoke(messages)  发起一次 HTTP 请求，得到 AIMessage
  → parser.invoke(msg)    提取 .content，得到 str
```
AIMessage 里除了 `.content`，还有 `.tool_calls`（工具调用请求）、`.response_metadata` / `.usage_metadata`（token 用量等）——调试时把整个对象 print 出来看一眼很有帮助。

### 4.2 create_agent 返回的是什么？——1.0 的 Agent 就是 LangGraph

实测：`create_agent(...)` 返回的对象类型是 `langgraph.graph.state.CompiledStateGraph`。也就是说 **LangChain 1.0 的 Agent 不再是 0.x 的 `AgentExecutor`（已随旧体系移入 langchain-classic），而是一张编译好的 LangGraph 状态图**：
- 状态（state）核心就是 `messages` 列表，所以 invoke 的输入是 `{"messages": [...]}`，输出也是包含全部中间过程的 `{"messages": [...]}`——user 消息、带 tool_calls 的 AIMessage、ToolMessage、最终 AIMessage 依次排列，这就是为什么"最终回答取 `res['messages'][-1].content`"、也是为什么遍历 messages 能还原完整推理链；
- 循环逻辑：模型节点 → 有 tool_calls？→ 工具节点执行 → 结果回模型节点 → 直到模型不再发起 tool_calls（输出纯文本）才停；
- 这解释了课程后面为什么要专门学 LangGraph：Agent 复杂了（分支、并行、人审、多智能体），就需要直接操作这张图。
（0.x 的 `create_react_agent` 也已并入新的 `langchain.agents` 体系，官方迁移说明：https://docs.langchain.com/oss/python/releases/langchain-v1）

### 4.3 为什么会有 langchain_classic？——1.0 的包架构

课件里一会儿 `langchain_core`、一会儿 `langchain_community`、一会儿 `langchain_classic`，没解释缘由。1.0 的拆分逻辑：
- **langchain-core**：最底层抽象（Runnable、Message、PromptTemplate、输出解析器）——所有包的公共依赖；
- **langchain**（1.x 本体）：精简后只保留最有用的高层入口，如 `create_agent`、`init_chat_model`、`langchain.tools`；
- **langchain-classic**：0.x 时代的旧链（ConversationChain 等）、旧 Memory、旧 Agent 工具函数整体搬到这里"养老"，保证老代码能跑；
- **langchain-community**：第三方集成大杂烩（ChatTongyi、SQLDatabase、各种工具）；
- **langchain-openai / langchain-ollama / langchain-deepseek**：单独拆包的官方 provider 集成。
判断标准很简单：**看到 `langchain_classic` 就知道是"旧时代 API，能用但别在新项目里用"**。

### 4.4 with_structured_output 和 PydanticOutputParser 是两条不同的路

课件把它们放在两章分别讲，没点破区别：
- `PydanticOutputParser`（4.4 节）：**prompt 工程路线**——把 format_instructions（一段"请输出这种 JSON"的文字）拼进 prompt，靠模型自觉遵守，返回后再解析校验。任何模型都能用，但可能失败。
- `with_structured_output`（2.6 节）：**原生能力路线**——把 Schema 转成 function calling 工具定义或 JSON mode 约束交给 API，由服务端在解码层保证格式。更可靠，但要求模型支持工具调用/JSON 输出。
优先用后者；前者用于不支持原生结构化输出的模型，或需要在 LCEL 链里显式插一个解析环节的场景。

### 4.5 bind_tools 没有"改造"模型

`llm.bind_tools([get_weather])` 返回的是**新的 Runnable**，它只是记住了"以后每次请求都把这些工具 Schema 附在请求体里"。原 llm 对象不变。这是 LangChain 里常见的"绑定参数"模式（还有 `.bind(stop=...)` 等）——组件不可变，配置通过包装叠加。理解这一点就不会疑惑"为什么还要一个新变量 llm_with_tools"。

### 4.6 ToolMessage 的 tool_call_id 为什么必须带

模型一次可能发起**多个** tool_calls（比如同时查两个城市天气）。回传结果时，每个 `ToolMessage(content=..., tool_call_id=...)` 靠 id 和对应请求配对，模型才知道哪个结果属于哪次调用。漏传或配错 id，API 会报错或模型会张冠李戴。这也是 6.6 节手动流程里 `messages.extend([response] + tool_results)` 必须把**模型的 AIMessage（含 tool_calls）也放回去**的原因——请求与响应必须成对出现在历史里。

## 五、Python 随堂补基础

**1. 装饰器（@tool 的原理）**：装饰器是"接收函数、返回新东西"的函数，`@x` 是语法糖。
```python
def loud(func):                # 接收一个函数
    def wrapper():
        return func().upper()  # 加工它的结果
    return wrapper             # 返回新函数

@loud                          # 等价于 hello = loud(hello)
def hello(): return "hi"
print(hello())                 # "HI"
```
`@tool` 更进一步：返回的不是函数而是一个 Tool 对象，所以 `get_weather.name`、`get_weather.invoke()` 这些属性方法才会存在。

**2. 类型注解（Schema 生成的原料）**：`:` 后写参数类型，`->` 后写返回类型。Python 运行时不强制检查，但 LangChain 靠它生成 JSON Schema（`location: str` → `"type": "string"`）。
```python
def add(a: int, b: int) -> int:
    return a + b
add("x", "y")   # 照样能跑！注解只是"标注"，不是强制
```

**3. Pydantic BaseModel（会强制校验的类型注解）**：
```python
from pydantic import BaseModel, Field
class Movie(BaseModel):
    title: str = Field(description="电影名")
    year: int
m = Movie(title="星际穿越", year="2014")  # "2014" 自动转成 int
print(m.year + 1)                          # 2015
Movie(title="x", year="abc")               # 报 ValidationError！
```
和普通类的区别：自动做类型转换和校验、能导出 JSON Schema——这正是结构化输出需要的。

**4. 运算符重载（`|` 为什么能连链）**：类定义了 `__or__` 方法，`a | b` 就会调用它。
```python
class Step:
    def __init__(self, f): self.f = f
    def __or__(self, other):               # 让 | 返回"组合后的步骤"
        return Step(lambda x: other.f(self.f(x)))
double = Step(lambda x: x * 2)
plus1  = Step(lambda x: x + 1)
print((double | plus1).f(5))               # 11 —— 迷你版 LCEL！
```

**5. 函数是"一等公民"（partial 传 get_datetime 不加括号）**：函数名本身是个值，可以赋值、当参数传。
```python
def now(): return "10:00"
x = now()   # 调用，x 是字符串 "10:00"（定格了）
y = now     # 引用，y 就是函数本身
print(y())  # 需要时再调用 —— partial(date=get_datetime) 用的就是这个
```

**6. lambda（RunnableWithMessageHistory 的工厂函数）**：一行匿名函数。
```python
f = lambda session_id: f"history-of-{session_id}"
# 等价于 def f(session_id): return f"history-of-{session_id}"
print(f("user_001"))
```
课件里 `lambda session_id: SQLChatMessageHistory(...)` 就是"给我 session_id，我给你对应的历史存储对象"。

**7. f-string 与花括号转义（4.4 节那个 `{{format_instructions}}`）**：
```python
name = "小明"
print(f"你好{name}")     # 你好小明 —— f-string 立即填充
print(f"你好{{name}}")   # 你好{name} —— 双花括号输出字面量 { }
```
课件在 f-string 里写 `{{format_instructions}}`，就是为了留下 `{format_instructions}` 这个字面占位符，让 LangChain 模板稍后再填。（其实那里不加 f 前缀直接写单括号更简单。）

**8. TypedDict（轻量版结构声明）**：
```python
from typing_extensions import TypedDict
class Movie(TypedDict):
    title: str
    year: int
m: Movie = {"title": "流浪地球", "year": 2019}  # 就是普通 dict，只是给类型检查器看
```

## 六、自测清单

**是什么：**
1. LangChain 六大核心模块分别是什么？各自一句话职责？
2. Chat Model 的输入输出分别是什么类型？和老式 LLM 接口的本质区别在哪？
3. System / Human / AI / Tool 四种消息各代表什么角色？
4. `prompt | llm | parser` 这条链 invoke 时，数据依次经历了哪几种类型的变换？
5. `@tool` 装饰器从函数里提取了哪三样东西来生成工具 Schema？

**为什么：**
6. 为什么说 temperature "改分布形状"而 top_k/top_p "砍候选词"？top_p 比 top_k 灵活在哪？
7. LLM 本来是无状态的，`ConversationBufferMemory` 凭什么能让它"记住"你？代价是什么？
8. Function Calling 里，工具到底是谁执行的？为什么模型"只决策不执行"是合理设计？
9. `ToolMessage` 为什么必须带 `tool_call_id`？
10. `with_structured_output` 为什么比"在 prompt 里求模型输出 JSON"更可靠？
11. `|` 运算符连接两个 Runnable 时，Python 层面发生了什么？返回的是什么对象？
12. 为什么 `partial(date=get_datetime)` 传函数名而不是 `get_datetime()`？两者行为差在哪？

**什么时候用：**
13. 什么时候用 `RunnableParallel`？它相比顺序执行两条链省的是什么？
14. 短期记忆和长期记忆（RunnableWithMessageHistory + 数据库）各适合什么场景？session_id 起什么作用？
15. 手写 bind_tools 循环 vs 直接 create_agent，各适合什么场景？（提示：学原理用前者，干活用后者）

## 七、动手小练习

**练习 1：三段式链 + 结构化输出（约 20 分钟）**
用 `deepseek-v4-flash`（或本地 Ollama 模型）搭一条链：输入任意一段自我介绍文字，输出 Pydantic 对象 `Person(name: str, job: str, skills: List[str])`。
要求：① 用 `ChatPromptTemplate` 写模板；② 分别用 `PydanticOutputParser`（拼 format_instructions）和 `with_structured_output` 各实现一次；③ 对比两种方式的代码量和稳定性，体会 4.4 节说的两条路线差异。

**练习 2：手动走一遍 Function Calling（约 30 分钟）**
定义两个工具：`add(a: int, b: int)` 和 `get_time()`（返回当前时间字符串）。**不用 create_agent**，只用 `bind_tools` + 手动循环：发送"现在几点了？另外 3+5 等于几？"，打印模型返回的 `tool_calls`（应该有两个），逐个执行并组装 `ToolMessage`（注意 tool_call_id），回传后打印最终回答。
进阶：把同样的需求丢给 `create_agent`，遍历返回的 `messages` 列表，对照你手动实现的每一步，验证 Agent 内部就是这套流程。

