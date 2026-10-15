# MCP（模型上下文协议）复习笔记
> 对应课件：2.MCP指南：从原理到实战.md

## 一、在知识体系中的位置

学 MCP 之前，你必须先把下面两个前置概念想清楚，否则一定会把 MCP 学拧巴：

- **Function Calling / Tool（工具调用）**：这是"大模型的一项能力"。模型在生成回复的过程中，判断"这个问题我自己答不了，需要调一个外部函数"，于是它**输出一段结构化的调用意图**（函数名 + 参数），比如 `weather_query(city="成都")`。注意：模型本身**并不执行**这个函数，它只是"说出来"。真正执行是你的代码干的。
- **Agent（智能体）**：能自主循环"思考 → 调工具 → 看结果 → 再思考"的程序。工具调用是 Agent 的核心动作。

**MCP 站在哪一层？** MCP 不是替代 Function Calling，而是**标准化"工具从哪来、怎么被发现、怎么被调用、结果怎么回"这一整套供给流程**。用一句话锚定：Function Calling 负责模型"说"，MCP 负责工具生态"供"。二者是上下游，不是竞争。这是本讲最容易被学员误解、也是最该记牢的一句话。

- **与 A2A 协议的分工区别**：MCP 解决的是"Agent ↔ 工具/数据源"的纵向连接；而 A2A（Agent-to-Agent）解决的是"Agent ↔ Agent"的横向协作。后续课件会讲 A2A，这里先建立一个坑位：MCP 管"工具供给"，A2A 管"智能体之间对话"，别混。
- **与 Agent Skills 的分工**（下一份笔记 12 会详讲）：MCP 管"外部能力怎么接进来"，Skills 管"某类任务该怎么做"。

---

## 二、核心知识点精讲

### 2.1 MCP 到底解决了什么"疼点"

课件开头那段 LangGraph 代码点出了真实痛点：**每个人都在重复造同一批工具轮子**。查天气、搜网页、读文件、发邮件——几乎所有 Agent 都要用，但没有统一标准，于是你封装一遍、隔壁组再封装一遍，API Key 一换代码就得改。

MCP 的定位就是课件那个绝妙的类比：**AI 工具生态里的 USB-C**。USB-C 统一了充电口的物理形状和引脚定义，任何设备任何线都能互插；MCP 统一了"工具怎么描述自己、怎么被发现、怎么被调用、结果怎么返回"的通信规范，于是**任何人写的 MCP Server，任何支持 MCP 的 Client 都能零适配直接用**。

> 补一个 2025 年底的重要背景（课件写作时还没发生）：2025 年 12 月 9 日，Anthropic 把 MCP 捐给了 Linux 基金会下新成立的 **Agentic AI Foundation（AAIF）**，MCP 从"某公司开源项目"正式变成"厂商中立的行业标准基础设施"。这也印证了 USB-C 类比的分量——它真的在往"通用接口"的方向走。

### 2.2 为什么"MCP ≠ 升级版 Function Calling"（本讲第一重点）

初学者最容易栽的坑，就是以为 MCP 是 Function Calling 的替代品。课件用了一个很好的拆法，我再帮你钉死：

| | Function Calling | MCP |
| --- | --- | --- |
| 本质 | 模型层的**能力**（feature） | 基础设施层的**通信协议** |
| 谁提供 | 模型厂商（OpenAI/DeepSeek/通义…） | 社区/厂商/你自己写的 Server |
| 标准化 | 各家 tools schema 略有差异 | 统一走 JSON-RPC 2.0 |
| 工具发现 | 代码里手动 `@tool` 写死 | Client 启动时 `tools/list` 动态拉取 |
| 运行位置 | 通常同进程直接调 | 独立进程（stdio 子进程 / 远程 HTTP） |
| 换模型 | 常要改 schema 适配 | 零改动，Client 帮你转格式 |

**一句话链路（务必背下来）：**
用户提问 → LLM 用 Function Calling 输出调用意图 → MCP Client 解析目标、构造 JSON-RPC 请求 → MCP Server 真正执行 → 结果原路返回 → LLM 用自然语言回复。

### 2.3 架构：四块积木

MCP 是典型 **Client-Server** 架构，逻辑上分四层：

- **Host（宿主）**：承载 LLM 和用户界面的应用（Claude Desktop、Cursor、你的 LangGraph 程序）。"用户在哪用、模型在哪跑"。
- **Client（客户端）**：Host 内部与每个 Server 建立**一对一**连接的组件。它是**双向翻译器**——往上把工具能力翻译成 LLM 能懂的 schema，往下把 LLM 的调用意图翻译成对具体 Server 的 RPC 请求。工具发现、调用路由、协议协商都在这层。
- **Server（服务端）**：真正干活的能力提供方，暴露 Tool / Resource / Prompt。
- **Base Protocol（基础协议）**：消息格式（JSON-RPC 2.0）、生命周期、传输方式的"语法书"。

> 补一个课件没强调的点：**一个 Client 只连一个 Server**。你挂多个 Server（课件里的 `MultiServerMCPClient`），本质是 Host 内部起了多个 Client 实例，各连各的。理解这点，后面"会话隔离""能力协商"就顺了。

### 2.4 协议层：JSON-RPC 2.0

MCP 所有消息都走 JSON-RPC 2.0，只有三种消息类型：

- **请求 Request**：有 `method`、有 `id`（像快递单号，用来匹配响应）。例：`tools/call`。
- **响应 Response**：带同一个 `id`，成功返回 `result`，失败返回 `error`（含标准错误码，如 `-32601` 方法不存在、`-32602` 参数无效、`-32700` 解析失败）。
- **通知 Notification**：只有 `method`、**没有 `id`**，单向推送不需回复。例：`notifications/resources/updated`。

选它的理由课件总结得很好：**轻**（纯 JSON 文本）、**简**（三种消息）、**透**（不绑定传输层）。

### 2.5 三个能力原语：Tool / Resource / Prompt

这是 Server 能暴露的三类东西，务必分清（课件把 Prompt 一笔带过，我在第四节补）：

- **Tool（工具）**：**LLM 自动决定何时调用**，有副作用的动作。查天气、算 BMI、发邮件。
- **Resource（资源）**：**开发者在代码里手动读取**的静态/模板化数据。配置、知识库、文档。通过 URI 定位，支持模板参数如 `knowledge://{topic}`。
- **Prompt（提示模板）**：预定义的提示词模板，通常由**用户主动选择**触发（如 slash 命令），课件没展开。

判断口诀：**"要不要 LLM 自己决定调" → 是就是 Tool；否则看数据是静态还是动态 → 静态走 Resource，动态/组装提示走 Prompt。**

### 2.6 上手代码要点

核心胶水库就一个：`langchain_mcp_adapters`，用 `MultiServerMCPClient` 同时挂多个 Server。

```python
mcp_client = MultiServerMCPClient({
    "amap": {"url": "https://.../mcp", "transport": "streamable_http"},  # 远程（注意：新版用 streamable_http，见第三节勘误）
    "my-tools": {"command": "python", "args": ["server.py"], "transport": "stdio"},  # 本地
})
tools = await mcp_client.get_tools()   # 自动发现，schema 自动生成，换模型不用改
```

- **Tool** 用 `await mcp_client.get_tools()` 拿到后直接丢给 Agent，LLM 自动调。
- **Resource** 要用 `async with mcp_client.session("name") as session:` 开会话，再 `await session.read_resource("knowledge://报销标准")` 手动读。

写自己的 Server 用官方 `FastMCP`：`@mcp.tool()` 装饰器自动把函数的**类型注解 + docstring** 抽成工具描述；`@mcp.resource("knowledge://{topic}")` 注册资源。

---

## 三、课件勘误与更新

### 已确认

**1. "MCP 官方定义了两类传输机制：stdio vs SSE" —— 已过时**
- 课件原文（4.2）：*"MCP 官方定义了两类传输机制……stdio ／ SSE（Server-Sent Events）"*，并在架构图、实战建议里都用 SSE。
- 问题类型：**已过时**（课件基于 2024-11-05 初版规范，当时确实是 stdio + HTTP+SSE，是对的；但现在变了）。
- 最新说法：MCP 在 **2025-03-26** 版规范中用 **Streamable HTTP** 取代了旧的 HTTP+SSE 传输，旧 SSE 传输被标记为 **deprecated（已弃用）**，仅为向后兼容保留。**当前规范只定义两种标准传输：`stdio` 和 `Streamable HTTP`**。Streamable HTTP 用单一端点（如 `/mcp`），客户端 POST 发 JSON-RPC，服务端按需返回 `application/json` 或升级成 `text/event-stream`（SSE 流）——也就是说 SSE 作为"底层技术"还在，但作为"独立的双端点传输模式"没了。
- 来源：[MCP 规范 · Streamable HTTP 传输](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)、[Why MCP Deprecated SSE and Went with Streamable HTTP](https://blog.fka.dev/blog/2025-06-06-why-mcp-deprecated-sse-and-go-with-streamable-http/)、[Auth0: MCP's Move Away from SSE](https://auth0.com/blog/mcp-streamable-http/)

**2. 代码里 `"transport": "sse"` + "部署上线用 SSE"的建议 —— 已过时**
- 课件原文（8. 实战建议）：*"本地开发用 stdio，部署上线用 SSE"*；代码中远程服务统一写 `"transport": "sse"`。
- 问题类型：**已过时**。
- 正确/最新说法：新项目远程传输应改用 Streamable HTTP。在 `langchain_mcp_adapters`（Python）里，取值写 **`"streamable_http"` 或 `"http"`**（注意是**下划线**，写成 `streamable-http` 连字符会报错）。`"sse"` 仍能用，但已被 MCP 规范标记为 deprecated，只建议用于"连接 2025 年 3 月前的老服务器"这种向后兼容场景。课件里连的魔搭 `.../sse` 端点在写作时是有效的，但现在的正解是优先找 `/mcp`（Streamable HTTP）端点。
- 来源：[LangChain MCP 文档](https://docs.langchain.com/oss/python/langchain/mcp)、[langchain-mcp-adapters Issue #322（transport 命名）](https://github.com/langchain-ai/langchain-mcp-adapters/issues/322)

**3. 架构图注释 "JSON-RPC 2.0 stdio / SSE" —— 同上，已过时**
- 同第 1 条，图中把传输标成 "stdio / SSE"，现应为 "stdio / Streamable HTTP"。来源同上。

### 更新（不算错，但需补充最新状态）

**4. "Anthropic 在 2024 年底开源" —— 正确，但需补后续**
- 事实无误：MCP 由 Anthropic 于 **2024 年 11 月**发布（首版规范号 `2024-11-05`）。补一个课件之后的大事：**2025-12-09 MCP 被捐给 Linux 基金会 Agentic AI Foundation**，治理转为厂商中立。
- 来源：[Anthropic: Donating MCP & establishing the AAIF](https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation)、[Linux Foundation 新闻稿](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation)

### 待核实

- **`create_agent` / `MultiServerMCPClient.get_tools()` 的确切 API 形态**：LangChain 在 1.0 前后对 `langchain.agents` 做过多次重构（`create_agent`、`create_react_agent` 等入口变动频繁）。课件示例语法在其写作版本正确，但当前最新版是否完全一致我未逐一比对 pip 版本，暂列待核实，跑代码前请以 `pip show langchain langgraph langchain-mcp-adapters` 的实际版本文档为准。
- **魔搭社区具体 MCP 服务 URL / API Key 要求**：课件给的 `mcp.api-inference.modelscope.net/xxx/sse` 是示例占位地址，实际端点会变，无法核实其时效，用时以魔搭 MCP 广场当下页面为准。
- **JSON-RPC `params` "可以是数组或对象"**：这是 JSON-RPC 2.0 基础规范的说法（本身没错），但 **MCP 的方法一律用对象形式的 `params`**，课件此处不算错但对 MCP 语境略不严谨，写自己的 Server 时按对象传即可。

---

## 四、课件没讲透的关键点补充

### 4.1 MCP 与 Function Calling 的真实关系：不是替代，是"标准化的工具供给"
课件讲了"上下游"，但没点透一层：即便有了 MCP，**Function Calling 依然存在且必需**。Client 从 Server 用 `tools/list` 拿到工具后，仍要把它转成模型厂商各自的 tools schema 喂给 LLM，LLM 仍然靠 Function Calling 能力"说出"要调哪个。MCP 做的是把"工具的来源和调用通道"标准化，**并没有取消 Function Calling 这一步**。记住这句：**MCP 标准化了工具的"供给侧"，Function Calling 仍是模型的"决策侧"。**

### 4.2 完整的 JSON-RPC 消息流（含初始化握手）
课件的时序图从"用户提问"开始，跳过了**连接建立阶段**。完整一次生命周期是：
1. **initialize**：Client 连上 Server，双方协商协议版本和能力（capabilities）。这一步决定"这个 Server 支持 tools 吗？支持 resources 吗？”
2. **initialized 通知**：Client 确认握手完成。
3. **tools/list**：拉取工具清单（也可 `resources/list`、`prompts/list`）。
4. **tools/call**：真正调用，带 `id`，等 `result`。
5. 运行中 Server 可发**通知**（如 `notifications/tools/list_changed`），Client 据此重新拉列表——这才是课件说的"动态发现"的底层机制。

补一个 2025-06-18 起的实操细节：走 HTTP 传输时，请求必须带 **`MCP-Protocol-Version` 头**声明协议版本，不带的话服务端按旧版 `2025-03-26` 语义兜底。来源：[MCP 传输规范](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)。

### 4.3 stdio 与 Streamable HTTP 的真正差异（更新版对照）
| 维度 | stdio | Streamable HTTP（新，取代 SSE） |
| --- | --- | --- |
| 通信 | Client 拉起 Server 子进程，走 stdin/stdout 管道 | 独立 HTTP 服务，单端点 POST + 可选 SSE 流 |
| 适用 | 本机工具（文件、本地 DB） | 远程/跨机器/容器化部署 |
| 延迟 | 极低（进程间管道） | 有网络开销 |
| 会话 | 进程生命周期即会话 | 可选 `Mcp-Session-Id` 头维护会话、支持断线重连 |

一句话：**本地用 stdio，远程用 Streamable HTTP**（课件说的"远程用 SSE"要更新成这句）。

### 4.4 为什么"安全隔离"是 MCP 的隐藏优势
课件提了一句"独立进程、崩溃不拖垮主程序"。再补透一点：直接 `import` 一个第三方工具包，等于把它的代码跑在你主进程里、共享你的内存和权限；而 MCP Server 跑在独立进程（甚至独立机器），**权限边界清晰、可沙箱、可限流**。这在企业级 Agent 里是刚需，不只是"崩溃不连带"这么简单。

---

## 五、Python 随堂补基础

本讲代码密集用到异步和装饰器，逐个给最小示例。

**1. 装饰器（decorator）** —— `@mcp.tool()` 的原理：把函数"包一层"再返回。
```python
def my_deco(func):
    def wrapper(*args, **kwargs):
        print("调用前")
        return func(*args, **kwargs)
    return wrapper

@my_deco          # 等价于 say = my_deco(say)
def say(): print("hi")
```

**2. 类型注解（type hints）** —— FastMCP 靠它自动生成工具 schema。
```python
def add(a: int, b: int) -> int:   # a、b 是 int，返回 int
    return a + b
```

**3. async / await** —— 定义和调用异步函数。
```python
import asyncio
async def fetch():          # async def 定义协程
    await asyncio.sleep(1)  # await 等待另一个协程
    return "done"
```

**4. asyncio.run()** —— 在同步入口启动异步世界。
```python
async def main(): ...
if __name__ == "__main__":
    asyncio.run(main())     # 顶层只调一次
```

**5. 异步上下文管理器 `async with`** —— 读取 Resource 时用，自动开/关会话。
```python
async with mcp_client.session("my-tools") as session:  # 进入时建连
    res = await session.read_resource("knowledge://报销标准")
# 退出时自动关闭连接，即使中间报错也会关
```

**6. 列表推导式** —— 课件里 `[t.name for t in tools]`。
```python
names = [t.name for t in tools]   # 把每个 tool 的 name 取出来组成新列表
```

---

## 六、自测清单

**是什么**
1. 用一句话说清 MCP 是什么？它像现实里的什么？
2. MCP 架构的四层分别叫什么，各管什么？
3. JSON-RPC 2.0 的三种消息类型分别有什么特征（谁有 id、谁没有）？
4. Tool、Resource、Prompt 三个原语的区别是什么？各举一例。
5. MCP 当前定义的两种标准传输是哪两种？

**为什么**
6. 为什么说"MCP 不是 Function Calling 的替代品"？二者各负责链路的哪一段？
7. 为什么 MCP 选 JSON-RPC 而不自己发明协议？
8. 为什么静态配置数据应该做成 Resource 而不是 Tool？
9. 为什么 SSE 传输被 Streamable HTTP 取代了？（提示：单端点 vs 双端点）
10. 为什么工具跑在独立进程里比直接 import 更安全？

**什么时候用**
11. 什么时候该用 stdio，什么时候该用 Streamable HTTP？
12. 什么时候该自己写 MCP Server，而不是用社区现成的？
13. 你要给 Agent 接一个"公司请假制度知识库"，该注册成 Tool 还是 Resource？为什么？
14. 换底座模型（DeepSeek → Qwen）时，用 MCP 的代码需要改哪里？为什么基本不用改？

---

## 七、动手小练习

**练习 A（约 20 分钟）：写一个最小 stdio MCP Server 并列出工具**
1. 用 `FastMCP` 写一个 `server.py`，注册两个工具：`get_time()` 返回当前时间、`word_count(text: str)` 返回字数。
2. 用 `MultiServerMCPClient` 以 `transport: "stdio"` 挂上它。
3. `await client.get_tools()` 打印工具名，确认两个工具都被自动发现。
4. 目标：亲手体会"装饰器 + 类型注解 → 自动生成 schema → 动态发现"这条链。

**练习 B（约 25 分钟）：把课件的 SSE 写法升级为 Streamable HTTP**
1. 把 `server.py` 的启动方式从 `mcp.run(transport="sse")` 改为 Streamable HTTP 模式（查 FastMCP 当前版本文档，通常是 `transport="streamable-http"`，端点在 `/mcp`）。
2. 客户端配置把 `"transport": "sse"` 改成 `"transport": "streamable_http"`（下划线！）、URL 指向 `/mcp`。
3. 跑通后对比：换传输方式后，你的**业务代码（工具定义、Agent 调用）一行都没改**——这就是 MCP 把传输层抽象掉的价值。
4. 若本机装的库版本还不支持，就在笔记里记录报错信息，作为"版本演进"的一手素材。
