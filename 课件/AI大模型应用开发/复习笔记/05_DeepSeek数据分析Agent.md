# DeepSeek 数据分析 Agent 复习笔记
> 对应课件：2.DeepSeek驱动的数据分析Agent实战.md
> 复习环境基准：langchain 1.3.1 / langchain-community 0.4.1（课件锁定的版本，PyPI 实查存在；笔记中"实测"均在此环境验证，2026-07）

## 一、在知识体系中的位置

**前置依赖：**
- 上一份课件的全部内容，尤其是：`create_agent`、`@tool` 自定义工具、Function Calling 消息流转、`invoke({"messages": [...]})` 的用法——本课件就是这些知识的第一次综合实战
- SQL 基础（SELECT / JOIN / GROUP BY 能看懂即可）
- Pandas / Matplotlib 的最基本用法（groupby、plot）

**后续哪些主题会用到它：**

| 后续模块 | 关系 |
| :--- | :--- |
| LangGraph | 7.1 节"编排器路由两个 Agent"是手写版的多节点工作流，LangGraph 就是把这种路由做成显式状态图（条件边、并行、循环） |
| Multi-Agent / A2A | 双 Agent 协作（SQL Agent + 可视化 Agent）是最小的多智能体系统；A2A 解决的是跨进程/跨厂商的 Agent 互通 |
| MCP / Agent Skills | 本课的 SQL 工具包、代码执行工具，在 MCP 时代会变成标准化的 MCP Server 能力 |
| 记忆系统 | 7.3 部署清单里"会话管理、多轮上下文"就靠记忆模块补齐 |
| RAG / Agentic RAG | 7.4 进阶方向明确提到：把数据字典、业务规则向量化，让 Agent 查库前先"懂业务"——这就是 Agentic RAG 的雏形 |

一句话：**这是"从会调 API 到会做系统"的转折课——学的不只是两个 Agent，而是"工具设计 + 安全边界 + 多 Agent 编排"这套工程思维。**

## 二、核心知识点精讲

### 2.1 业务问题：为什么值得做数据分析 Agent

传统链路的核心矛盾：**懂业务的人不会写 SQL/代码，会写代码的人要排队接需求**。LLM 恰好补上三层能力：自然语言理解（把"上月各区域销售情况"解析成 时间范围+分组维度+指标）、代码生成（意图 → SQL / Python）、推理规划（复杂问题拆步骤）。分工记住一句话：**LLM 负责"理解"和"生成"，Agent 框架负责"调度"和"执行"**。

### 2.2 系统架构：两个 Agent 各管一段

- **NL2SQL Agent**：自然语言 → SQL → 查库 → 用中文总结。工具来自现成的 `SQLDatabaseToolkit`。
- **可视化 Agent**：结构化数据 → Python 分析/画图代码 → 沙箱执行 → 解读结果。工具是自定义的 `execute_python_code`。
- 上面套一个**编排器**做意图路由（query / visualize / both）。

为什么拆成两个而不是一个全能 Agent？工具越多，模型选错工具的概率越大、system prompt 越臃肿；按职责拆分后每个 Agent 的提示词短而专。课件 7.1 方案 B（单 Agent 挂全部工具）就是留给你体会"选择困难"问题的作业。

### 2.3 NL2SQL Agent：工具链让模型"先侦察再动手"

`SQLDatabaseToolkit(db=db, llm=llm)` 自动注册 4 个工具（实测名称无误）：
- `sql_db_list_tables`：列出所有表
- `sql_db_schema`：查指定表的 DDL 结构
- `sql_db_query_checker`：执行前用 LLM 检查 SQL 语法（这就是 toolkit 构造时要传 llm 的原因——这个工具内部要再调一次模型）
- `sql_db_query`：真正执行 SQL

Agent 的标准动作序列：**list_tables（有什么表）→ schema（字段长什么样）→ 生成 SQL → query_checker（自检）→ query（执行）→ 中文总结**。这是 ReAct 思想的落地：不是一步到位生成答案，而是"侦察 → 行动 → 验证"的循环。System Prompt 里把这个流程和约束（只用真实存在的字段、限制 50 条、出错要自我修正）写成"岗位说明书"，是让 Agent 靠谱的关键——**Agent 的可靠性 = 工具质量 × 提示词质量**。

`SQLDatabase.from_uri(...)` 底层是 SQLAlchemy，URI 格式为 `方言+驱动://用户:密码@主机:端口/库名`（如 `mysql+pymysql://...`），所以理论上换 PostgreSQL/SQLite 只用改 URI。

### 2.4 可视化 Agent：核心是"代码执行沙箱"这个自定义工具

设计思路三步：
1. **准备执行环境**：把三张表提前查成 DataFrame（employees_df 等），连同 pd/plt/sns/np 一起放进 `SANDBOX_GLOBALS` 字典，作为代码可见的变量集合；
2. **定义工具**：`@tool execute_python_code(code: str) -> str`，用 `exec()` 执行模型生成的代码，用 `StringIO + redirect_stdout` 把所有 `print()` 输出捕获成字符串返回给 Agent；
3. **错误回传**：except 里返回完整 `traceback.format_exc()`——**这不是给人看的，是给 Agent 看的**，它拿到报错栈才能自我修正重试。这是"让 Agent 自愈"的关键设计。

工具 docstring 里详细列出可用变量、字段名、示例代码——再次印证上一课的要点：**docstring 是写给模型的说明书**。模型只有"看过说明书"才知道环境里有 `employees_df` 这个变量可以直接用。

### 2.5 编排器：最简版 Multi-Agent

`run_data_analysis(user_query)` 先用一次裸 LLM 调用做三分类（query / visualize / both），再路由：
- query → SQL Agent；
- visualize → 可视化 Agent；
- both → **先 SQL Agent 查数，把查询结果文本拼进新 prompt 喂给可视化 Agent**——注意两个 Agent 之间传递的是"上一个 Agent 的最终回答文本"，这是最朴素的 Agent 间通信方式（后续 LangGraph/Multi-Agent 模块会给出共享状态等更优雅的方案）。

### 2.6 安全与工程化（面试高频）

| 风险 | 措施 |
| :--- | :--- |
| SQL 注入 / 误删数据 | 数据库账号只授 SELECT 权限；LIMIT 限制返回行数 |
| 恶意/失控代码 | Demo 用 exec，生产必须 Docker 容器或 WASM 隔离（限 CPU/内存/网络） |
| Key 泄露 | 环境变量（`os.getenv`），永不硬编码 |
| 数据泄露 | 按用户角色控制可查数据范围 |
| 滥用 | 速率限制、日志审计、监控告警 |

`temperature=0` 的用意：SQL/代码生成是确定性任务，要稳定可复现，不要创造力。（但注意：对 DeepSeek V4 默认状态该参数不生效，见勘误第 2 条——需先关闭思考模式。）

## 三、课件勘误与更新

1. **课件原文**（2.3 技术栈表）："大模型：DeepSeek-Chat / DeepSeek-Coder"
   **问题类型**：已过时
   **正确/最新说法**：DeepSeek API 当前只提供 `deepseek-v4-flash` 与 `deepseek-v4-pro` 两个模型（独立的 deepseek-coder 模型线早已合并入主模型）。`deepseek-chat`、`deepseek-reasoner` 这两个模型名已于 2026-07-24 弃用（为兼容暂映射到 v4-flash 的非思考/思考模式）。课件代码里实际用的 `deepseek-v4-flash` 是当前正确写法，技术栈表述应同步更新。
   **来源**：https://api-docs.deepseek.com/quick_start/pricing

2. **课件原文**（3.2 节）：`temperature=0,  # 设为 0 保证 SQL 生成的确定性`
   **问题类型**：已过时/不严谨
   **正确/最新说法**：DeepSeek V4 系列**默认开启思考（thinking）模式**，思考模式下 `temperature`、`top_p` 等采样参数**被静默忽略（不报错、不生效）**。想让 `temperature=0` 真正起作用，需关闭思考模式：`ChatOpenAI(..., temperature=0, extra_body={"thinking": {"type": "disabled"}})`。另外对 NL2SQL 这类"快、稳、便宜"的场景，关闭思考模式也能显著降低延迟与 token 消耗；复杂分析则可保留思考模式（此时确定性靠思考链本身而非温度）。
   **来源**：https://api-docs.deepseek.com/guides/thinking_mode

3. **课件原文**（6.3 节）：`exec(code, exec_globals, exec_locals)`（globals 与 locals 传两个不同的字典）
   **问题类型**：错误（潜藏 bug，Agent 生成的代码很容易触发）
   **正确/最新说法**：当 exec 的 globals 和 locals 是两个不同对象时，Python 按"类定义体"的作用域规则执行代码：**顶层赋值进了 locals，但代码里定义的函数、列表/字典推导式在查找变量时只找 globals 和自己的局部作用域，找不到 locals 里的顶层变量**。实测复现：`exec("x=1\ndef f(): return x\nf()", g, l)` 抛 `NameError: name 'x' is not defined`。Agent 生成的分析代码一旦定义辅助函数或用推导式引用前面定义的变量就会莫名报错。修复：只传一个命名空间——`exec(code, exec_globals)`（新变量也会落在 exec_globals 里，同样能实现"收集执行产物"）。
   **来源**：https://docs.python.org/3/library/functions.html#exec （"If exec gets two separate objects as globals and locals, the code will be executed as if it were embedded in a class definition."）

4. **课件原文**（6.3 节注释）："这是一种简单的安全策略：不在白名单里的东西，代码碰不到"
   **问题类型**：不严谨（安全性表述错误）
   **正确/最新说法**：给 exec 传自定义 globals **并不构成安全边界**。Python 规定：globals 字典若不含 `__builtins__` 键，解释器会自动插入完整的内置函数表——因此沙箱内代码依然可以 `import os`、`open()` 读写文件、发网络请求。这个"白名单"的真实作用只是**把 DataFrame 和常用库预置为可见变量**（提供便利），不是拦截机制。课件 6.3 末尾的安全提示（生产用 Docker/WASM）是对的，但正文这句表述会让学员误以为 exec 白名单能防恶意代码。真正的隔离必须在进程/容器层面做。
   **来源**：https://docs.python.org/3/library/functions.html#exec （"If the globals dictionary does not contain a value for the key `__builtins__`, a reference to the dictionary of the built-in module builtins is inserted under that key."）

5. **课件原文**（5.2 节注释）：`from langchain.agents import create_agent  # langchain 1.3.1 的新 API`
   **问题类型**：不严谨
   **正确/最新说法**：`create_agent` 是 LangChain 1.0（2025-10 正式发布）引入的核心 Agent API（取代 0.x 的 AgentExecutor 体系），并非 1.3.1 才新增。1.3.1 只是课件锁定的一个具体版本（PyPI 实查该版本存在，当前最新为 1.3.14）。
   **来源**：https://docs.langchain.com/oss/python/releases/langchain-v1

**版本与事实确认（不是勘误）**：① `SQLDatabaseToolkit` 注册的 4 个工具名（sql_db_list_tables / sql_db_schema / sql_db_query_checker / sql_db_query）与课件所列完全一致（本地实测）；② `create_agent(model=..., tools=..., system_prompt=...)` 签名正确、`invoke({"messages": [...]})` 输入格式正确、"无需再套 AgentExecutor"的说法正确（1.0 后 AgentExecutor 已移入 langchain-classic 弃用体系）。

### 待核实
- 课件三张架构图（系统架构图.png、ER关系图.png、NL2SQL工作流.png 等）为本地图片文件，课件目录中未随附，图中内容无法核对。
- "executemany 批量插入，比逐条 insert 高效得多"：mysql-connector-python 对 INSERT 的 executemany 确实有多值语句优化的说法，但具体性能倍数未做基准测试，保留说法方向、不背书具体程度。
- `plt.show()` 在无显示器环境（服务器/容器）下的具体行为依 matplotlib 后端而定（Agg 后端下静默不显示）；课件在本机 Demo 场景可弹窗，生产行为需按部署环境验证。

## 四、课件没讲透的关键点补充

### 4.1 Agent 循环到底何时停？

`create_agent` 返回的是 LangGraph 编译图（实测类型 `CompiledStateGraph`），内部循环规则：模型输出若带 `tool_calls` → 执行工具 → 把 ToolMessage 追加进状态 → 再调模型；**直到模型输出一条不带 tool_calls 的纯文本 AIMessage，循环结束**。这就是"示例 1 简单计数只跑一两轮、复杂 JOIN 会跑四五轮"的原因——轮数由模型自己决定。防失控：LangGraph 有递归上限（默认 25 步），超限抛错，生产中还应加超时与费用监控。这也解释了 5.4 节调试代码为什么"遍历 messages 就能还原推理链"——**整个循环的每一步都以消息形式留在状态里**。

### 4.2 Agent 根本"看不见"它画的图

一个课件完全没点破、但学员一定会疑惑的问题：可视化 Agent 的工具返回值是**字符串**（stdout 捕获），`plt.show()` 弹出的图像**不会**回传给模型——模型只知道"代码执行成功（无文本输出，可能已生成图表）"。所以：
- Agent 对图表内容的"解读"其实来自它 print 出的统计量，不是看图；
- 无显示器的服务器上 `plt.show()` 什么都不会发生，生产做法是 `plt.savefig("output.png")` 后返回文件路径（或 base64），由前端展示；
- 想让模型真"看图"，需要多模态模型 + 把图片编码进消息——那是另一套成本更高的方案。
这个认知对后面所有"Agent 生成产物"的场景（文件、图片、网页）都适用：**工具返回什么，模型就只知道什么**。

### 4.3 沙箱里的数据是"快照"，不是实时库

`employees_df` 等是在搭沙箱时一次性 `pd.read_sql` 拉进内存的。之后数据库再有增删改，可视化 Agent 分析的仍是旧数据；而 SQL Agent 每次都现查库。两个 Agent 对同一问题可能给出不一致的答案——生产中要么定时刷新 DataFrame，要么让可视化工具也现场查库。这也是 both 路由"先查库再喂给可视化 Agent"的一个隐含理由：用最新查询结果而不是快照。

### 4.4 真沙箱和 exec 的差距到底在哪

exec 方案缺的不是"白名单"（见勘误 4，那不是安全机制），而是四层隔离：**权限隔离**（读写文件/网络）、**资源隔离**（CPU/内存上限，防 `while True`）、**进程隔离**（崩溃不拖垮主程序）、**环境隔离**（依赖冲突）。Docker 方案 = 每次执行起一个受限容器，代码通过挂载/stdin 传入，结果通过 stdout/文件取回，超时强杀。理解这个分层，7.3 部署清单里"沙箱替换为 Docker 容器（限制 CPU/内存/网络）"这一条才不是一句空话。

### 4.5 SQLDatabaseToolkit 的隐性 token 成本

Agent 每答一个问题都要走 list_tables + schema 两轮"侦察"，表多、字段多时 schema 文本非常长，token 花费和延迟都会涨。优化思路：把常用表结构直接写进 system prompt（省去侦察轮次）、限制 toolkit 可见的表（`SQLDatabase.from_uri(..., include_tables=[...])`）、缓存 schema。7.4 说的"数据字典做成向量库（RAG 增强）"是更彻底的方案：按问题检索相关表结构，而不是全量塞。

### 4.6 编排器分类的脆弱性

意图三分类靠一次裸 LLM 调用返回 "query/visualize/both" 单词。现实中模型可能返回"这是 query 类型"甚至带思考过程的长文本，`.strip().lower()` 就匹配不上了，代码会静默落入 else 分支（both）。健壮做法：用上一课的 `with_structured_output`（枚举字段）做分类，或至少用 `in` 判断包含关系。这是"Demo 代码"与"生产代码"的典型差距，也顺便复习了结构化输出的价值。

## 五、Python 随堂补基础

**1. os.getenv 与默认值（读环境变量）**：
```python
import os
key = os.getenv("DEEPSEEK_API_KEY")          # 没设置时返回 None
host = os.getenv("DB_HOST", "127.0.0.1")     # 第二个参数是默认值
port = int(os.getenv("DB_PORT", 3306))       # 环境变量都是字符串，要手动转 int
```

**2. 相邻字符串自动拼接（db_uri 那段的写法）**：括号内两个字符串字面量挨着写，Python 自动拼成一个。
```python
uri = (
    "mysql+pymysql://root:pwd"
    "@localhost:3306/mydb"       # 没有加号！自动拼接
)
print(uri)  # mysql+pymysql://root:pwd@localhost:3306/mydb
```

**3. exec 与命名空间（沙箱的核心）**：exec 把字符串当代码跑，第二个参数决定代码"能看见哪些变量"。
```python
env = {"x": 10}
exec("y = x * 2\nprint(y)", env)   # 20 —— 代码只认识 env 里的东西
print(env["y"])                     # 20 —— 新变量也落回 env
```
注意：globals/locals 传两个不同字典有作用域大坑（见勘误 3），传一个就够。

**4. 上下文管理器 with（redirect_stdout 捕获 print）**：`with` 保证"进入时做准备、退出时自动收尾"。
```python
from io import StringIO
from contextlib import redirect_stdout
buf = StringIO()                      # 内存里的"假文件"
with redirect_stdout(buf):            # 这段时间 print 都写进 buf
    print("hello")
print(buf.getvalue())                 # "hello\n" —— 拿到了捕获的输出
```

**5. try / except / traceback（把报错变成字符串喂给 Agent）**：
```python
import traceback
try:
    1 / 0
except Exception as e:
    print(type(e).__name__, e)          # ZeroDivisionError division by zero
    text = traceback.format_exc()       # 完整错误栈的字符串版
```

**6. dict() 浅拷贝（每次执行都给新环境）**：
```python
base = {"a": 1}
env = dict(base)      # 复制一份，改 env 不影响 base
env["a"] = 99
print(base["a"])      # 1
```
沙箱里 `exec_globals = dict(SANDBOX_GLOBALS)` 就是防止某次执行污染公共环境。注意这是浅拷贝：字典本身是新的，但里面的 DataFrame 还是同一个对象，代码若原地修改 df 会影响后续执行。

**7. 反射三件套（5.4 调试代码用的）**：
```python
msg = "hi"
print(msg.__class__.__name__)     # 'str' —— 拿对象的类名
print(hasattr(msg, "upper"))      # True —— 有没有某属性
print(getattr(msg, "upper")())    # 'HI' —— 按名字取属性再调用
```
调试 Agent 消息时用它区分 AIMessage / ToolMessage。

**8. 切片防刷屏**：
```python
s = "x" * 1000
print(s[:200])     # 只打印前 200 个字符 —— msg.content[:200] 同理
```

## 六、自测清单

**是什么：**
1. 本系统的两个 Agent 各自的输入、输出、核心工具是什么？
2. `SQLDatabaseToolkit` 自动注册哪 4 个工具？各自干什么？
3. NL2SQL Agent 回答"每个部门各有多少人"时，标准的工具调用顺序是什么？
4. 可视化 Agent 的 `execute_python_code` 工具返回给模型的到底是什么？图片会回传吗？
5. 编排器把用户问题分成哪三类？"both"类的执行链路是怎样的？

**为什么：**
6. 为什么 SQL 生成任务要 `temperature=0`？在 DeepSeek V4 上这样设置默认为什么不生效、怎么改？
7. `SQLDatabaseToolkit` 构造时为什么必须传 llm？哪个工具用到了它？
8. 工具执行出错时为什么要把完整 traceback 返回给 Agent，而不是返回"执行失败"四个字？
9. `exec(code, g, l)` 传两个不同字典会引出什么 bug？为什么只传一个就没事？
10. 为什么说"exec + globals 白名单"不是安全机制？真正的沙箱要隔离哪四样东西？
11. 为什么拆成两个专职 Agent，而不是把所有工具挂到一个 Agent 上？
12. Agent 循环是靠什么条件终止的？为什么还需要递归上限兜底？

**什么时候用：**
13. 什么时候该把表结构写死进 system prompt，什么时候让 Agent 自己调 sql_db_schema 侦察？
14. 什么情况下编排器可以用规则/关键词路由代替 LLM 分类？各有什么代价？
15. Demo 沙箱（exec）和 Docker 沙箱的分界线在哪——什么信号出现时必须切换？

## 七、动手小练习

**练习 1：SQLite 版 NL2SQL Agent（约 30 分钟）**
不装 MySQL，用 SQLite 零配置复刻 5.2 节：
① `SQLDatabase.from_uri("sqlite:///demo.db")`，用 sqlite3 建 employees 一张表灌 5 条数据；
② `SQLDatabaseToolkit` + `create_agent` 组装 Agent（模型用 `deepseek-v4-flash`，加上 `extra_body={"thinking": {"type": "disabled"}}` 并设 `temperature=0`，体会勘误 2）；
③ 提问"薪资最高的员工是谁？"，然后遍历 `response["messages"]` 打印每一步，数一数它调了几次工具、生成的 SQL 长什么样。

**练习 2：修好沙箱的两个坑（约 25 分钟）**
① 先复现 bug：按课件原样写 `exec(code, exec_globals, exec_locals)`，让工具执行这段代码——
```python
tax_rate = 0.1
def after_tax(s): return s * (1 - tax_rate)
print(after_tax(20000))
```
观察 NameError；② 改成 `exec(code, exec_globals)` 验证修复；③ 再验证"白名单不是安全墙"：执行 `import os; print(os.getcwd())`，发现照样能跑通，写一句话总结为什么（对照勘误 4）。

