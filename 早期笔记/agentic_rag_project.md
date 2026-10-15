# Agentic RAG 多源检索项目实战 — 学习笔记（完整版）

> 课件：`课件\...\7.A2A 架构与 Agentic RAG 项目实战\3.Agentic RAG 多源检索项目实战.md`
> 代码：`C:\workspace\Agentic_Rag`（注意：`C:\workspace\a2a` 是本模块第 1 课 A2A 协议的演示代码，本课用不到）
> 前置笔记：`rag 学习.md`（RAG 基础）、`langgraph_course.md`（LangGraph）、`multi-agent 学习.md`、`a2a 学习.md`
> 学习日期：2026-07-25。全部代码已逐文件通读，数据已手工核对，关键论断已联网核实。

---

## 目录

1. [先看这里：仓库 Bug 与课件甄别结果](#一先看这里仓库-bug-与课件甄别结果)
2. [本课定位：它和前面学的东西是什么关系](#二本课定位)
3. [全景架构：业务、七类问题、执行链路](#三全景架构)
4. [逐层讲解（按数据流顺序）](#四逐层讲解)
5. [测试解读：每个测试在锁死什么](#五测试解读)
6. [运行手册：把项目跑起来](#六运行手册)
7. [开发思维框架：以后自己做这类系统怎么想](#七开发思维框架)
8. [课后作业实施指南：VPN 故障诊断助手](#八课后作业实施指南)
9. [Python 知识点汇总](#九python-知识点汇总)
10. [自测题（附答案）](#十自测题)

---

## 一、先看这里：仓库 Bug 与课件甄别结果

### 🐛 Bug 1（必修）：`app/config.py:38` 语法错误，整个项目跑不起来

```python
embedding_model_name: str = (
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)7          # ← 行尾多了一个 7 → SyntaxError: invalid syntax
```

- 已用 `git status` 确认工作区干净、仓库只有一个 init 提交 → **这是老师提交时就带的错误**，不是本地改坏。
- 已用 `python -m py_compile app/config.py` 复现报错。
- `config.py` 是全项目的依赖入口（所有模块都 import 它），所以**删掉这个 `7` 之前，任何脚本、测试、API 都无法启动**。
- 修法：删掉 `7` 即可。
- 教训：**拿到课程仓库先编译/跑测试，别默认它能跑。**

### ⚠️ 甄别 2：课件第七节"证据不足案例 1"（物流查询）在默认 demo 引擎下不成立

课件说 "U1001 的订单 O2026001 现在配送到哪里" 的预期路由是 `SQL_QUERY + MILVUS_SEARCH`，最终 `termination_reason=retrieval_budget_exhausted`。

**实际跑 demo 引擎不是这样**。看 `app/decision_engine.py:67-68` 的两张关键词表：

```python
SQL_TERMS = ("订单", "几单", "多少单", "实付", "总额", "金额", "统计", "最近")
DOC_TERMS = ("规则", "政策", "退货", "退款", "运费", "包邮", "价保", "售后")
```

"配送到哪里，预计几点送达" 这句话里：命中 `SQL_TERMS` 的只有"订单"；`DOC_TERMS` 一个都不命中（表里没有"配送""物流""送达"）。所以 demo 引擎的实际路由是 **`[SQL_QUERY]` 单源**，SQL 又总能返回 Evidence（哪怕 0 单也是一条统计结果），Grader 来源检查通过 → **accept → 生成完整答案**，根本不会走到"预算耗尽输出部分答案"。

容易踩的坑：`POLICY_KEYWORDS`（`decision_engine.py:20-24`）里的 shipping_policy 确实包含"配送、物流、送达"，但那张表**只用于提取 policy_type 槽位**，不参与"要不要查文档"的路由判断。两张关键词表长得像、用途完全不同。

**结论**：课件描述的行为需要 **DeepSeek 引擎（LLM 路由 + LLM Grader）** 才可能复现。课件没有说明这个前提，用默认 demo 模式验收会对不上。

### ⚠️ 甄别 3：案例 2（售后审核）demo 引擎下路由对，但结论不对

"AirBuds Pro 订单是否已通过售后审核" 命中"订单"（SQL）+"售后、退款"（DOC）→ 路由 `[MILVUS_SEARCH, SQL_QUERY]` 与课件一致 ✓。
但两个源都会返回 Evidence，而 demo Grader（`decision_engine.py:224-275`）只做两件事：**来源覆盖检查 +
Milvus 分数门槛检查**。来源齐了、分数够了就 accept。它**没有能力**判断"证据虽然有、但覆盖不了'审核状态'这个目标"——这种**语义级缺口**（课件说的"实时性、对象一致性、关键业务状态"）只有 LLM Grader 有机会识别。

这不是代码 bug，而是**课件把 LLM 引擎的能力当成了系统默认行为来描述**。理解这一点反而是本课最有价值的知识点之一：
> **确定性 Grader 便宜、稳定、可测试，但只能查"形式完整性"；语义充分性必须靠 LLM（或更多规则）。生产系统通常两层都要。**

### ✅ 甄别 4：已核实为真的关键论断（有真实来源）

| 论断 | 核实结果 |
| --- | --- |
| `deepseek-v4-flash` 模型存在 | 真。2026 年 4 月 DeepSeek 发布 V4 Preview：V4-Pro（1.6T 总参/49B 激活）、V4-Flash（284B 总参/13B 激活），1M 上下文。见 [DeepSeek 官方公告](https://api-docs.deepseek.com/news/news260424/) |
| 老模型名退役 | `deepseek-chat` / `deepseek-reasoner` 已于 **2026-07-24**（就在昨天）退役，分别对应 v4-flash 的非思考/思考模式。项目直接用新模型名是对的 |
| `extra_body={"thinking": {"type": "disabled"}}` 写法 | 真，官方文档的标准写法。V4-Flash **默认开启 Thinking**，所以想关必须显式传 disabled |
| "Thinking 模式与强制 tool_choice 冲突" | 真。V4 思考模式下传 `tool_choice="required"`/指定函数会直接 400（"Thinking mode does not support this tool_choice"），LangChain 的 `with_structured_output(method="function_calling")` 正是强制 tool_choice，所以项目里路由/评分必须关 Thinking。见 [deepseek-ai/DeepSeek-V3#1376](https://github.com/deepseek-ai/DeepSeek-V3/issues/1376) |
| U1001 数据 | 真。手工核对 `orders.csv`：最近 30 天有效订单 = 6999+1299+199+1899 = **4 笔 / 10396 元**，59 元那笔是 cancelled 不计，35 天前那笔超窗口，低于 99 元有效订单 0 笔。与课件、与 `test_sql_store.py` 三方一致 |

### 📝 甄别 5：小出入（不算错，对照时注意）

- 课件里的 SQL 片段比实际代码（`sql_store.py:164-174`）少了一列 `GROUP_CONCAT(order_id) AS order_ids`。
- 课件和 README 都说"项目默认 demo 引擎、无需 Key"，指的是**代码默认值**（`config.py: llm_provider: str = "demo"`）。但本仓库 checked-in 的 `.env` 写了 `LLM_PROVIDER=deepseek` 且配了 key——**你实际跑起来走的是 DeepSeek**。想先用确定性模式学习，把 `.env` 改回 `LLM_PROVIDER=demo`。顺带说：把 `.env`（含真实 key）提交进 git 本身就是反面教材，README 自己都说"不要提交 .env"。
- `requires-python = ">=3.11,<3.13"`：因为用了 `StrEnum`（3.11 新增）等特性，Python 3.10 跑不了。

---

## 二、本课定位

这门课到这里，你已经学了四块积木，本课是把它们拼成一个**能验收的完整系统**：

| 前置课 | 你学到的 | 在本项目里变成 |
| --- | --- | --- |
| RAG 基础（`rag 学习.md`） | 向量化、切分、检索、重排 | `milvus_store.py` + `embeddings.py`，但检索只是三个工具之一 |
| LangGraph（`langgraph_course.md`） | StateGraph、节点、条件边、State | `graph.py`：整个控制流就是一张状态图 |
| Multi-Agent / A2A | 职责拆分、协议化通信 | 本课不用 A2A，但"大脑与骨架分离"的思想同源 |
| 上一课《Agentic RAG 核心机制》 | 五项能力的**概念** | 本课是五项能力的**代码落地**（映射见下表） |

上一课的五项能力 → 本项目代码的映射（重要，面试常问）：

| 五项能力 | 落地位置 | 实现方式 |
| --- | --- | --- |
| 1. 意图识别与路由 | `DecisionEngine.route()` | demo=关键词规则；deepseek=Function Calling 输出 `RouteDecision` |
| 2. 自适应检索 | `DecisionEngine.plan()` | 把路由结果翻译成带参数的 `PlanStep` 列表 |
| 3. 工具调用 | `tools.py` 三个 Tool + 两个 Store | 受控参数、异常→`ToolResult` |
| 4. 自我反思 | `DecisionEngine.grade()` + `grade_evidence` 节点 | 来源覆盖+分数门槛（demo）/LLM 评分（deepseek），程序层强制预算 |
| 5. 多步推理 | `plan_query`→`execute_plan` 并行执行 | 无依赖步骤进线程池；（本项目没做依赖 DAG，课件明说要拓扑批次） |

> 记住课件那句话：**五项能力不是五个 Agent**。这个项目里它们是同一个引擎对象上的五个方法 + 一张图上的几个节点。

---

## 三、全景架构

### 1. 业务与三个数据源

电商售后助手，一个问题入口，背后三类数据：

| 数据源 | 存什么 | 工具名 | 为什么必须是它 |
| --- | --- | --- | --- |
| Milvus | 内部政策（退货/运费/价保 3 份 md） | `milvus_search` | 语义问题（"拆封了还能退吗"）靠向量相似度 |
| SQLite | 脱敏订单表 | `sql_query` | **精确统计不能靠语义相似度**，COUNT/SUM 必须是确定性 SQL |
| Tavily | 公开网页 | `web_search` | 官网最新公告不在任何内部库里，静态知识库天然过期 |

### 2. 七类问题（系统的"需求规格"）

| # | 类型 | 例子 | 预期行为 |
| --- | --- | --- | --- |
| 1 | 单源-向量 | 耳机拆封后还能七日无理由退货吗 | 只调 Milvus |
| 2 | 单源-SQL | U1001 最近 30 天几笔有效订单 | 只调 SQLite |
| 3 | 单源-Web | 官网关于 XPhone 15 Pro 的最新公告 | 只调 Tavily |
| 4 | 双源 | 统计订单 + 结合运费规则说是否包邮 | Milvus + SQLite 并行 |
| 5 | 三源 | 统计订单 + 退货政策 + 官网公告 → 售后建议 | 三工具并行 |
| 6 | 证据不足 | 订单现在配送到哪里 | 工具都成功也不能硬答（缺物流 API） |
| 7 | 证据不足 | 售后审核过了吗、退款哪天到账 | 同上（缺售后 API） |
| + | 澄清 | "我最近买了几单"（没有 user_id） | CLARIFY，不碰任何工具 |
| + | 拒绝 | "导出所有买家手机号" | REFUSE，不碰任何工具 |

### 3. 执行链路（`graph.py` 的那张图）

```
START → normalize_query → route_query ──┬─ clarify ────────────────→ END
                                        ├─ refuse ─────────────────→ END
                                        ├─ generate_answer（免检索）→ END
                                        └─ plan_query → execute_plan → grade_evidence
                                               ↑            (并行执行工具)     │
                                               │                             ├─ accept → generate_answer → END
                                               └──── rewrite_query ←────────┤  (rewrite_query 且还有预算)
                                                                             └─ stop → generate_partial_answer → END
```

### 4. 文件地图（谁负责什么）

| 文件 | 角色 | 一句话职责 |
| --- | --- | --- |
| `app/schemas.py` | 合同 | 所有模块间传递的结构化数据（Pydantic 模型） |
| `app/config.py` | 配置 | `.env` → `Settings`，路径锚定项目根，密钥用 SecretStr |
| `app/decision_engine.py` | 大脑 | route/plan/grade/rewrite/answer 五个决策，demo 和 deepseek 可互换 |
| `app/graph.py` | 骨架 | LangGraph 节点+边，控制流、并行、预算强制、trace |
| `app/tools.py` | 手 | 三个工具适配器，异常统一转 `ToolResult` |
| `app/milvus_store.py` / `app/sql_store.py` | 库 | 受控 Filter / 受控 SQL 模板，结果转 Evidence |
| `app/embeddings.py` | 向量 | Hash（演示/测试）和 SentenceTransformer 两种 Provider |
| `app/service.py` | 组装 | 依赖注入 + 每请求独立初始 State |
| `app/main.py` / `app/cli.py` | 入口 | FastAPI `/query`、命令行 `--debug` |
| `scripts/prepare_data.py` | 数据 | CSV→SQLite、md→切分→Milvus，全量重建 |
| `tests/` | 锁 | 用 Fake 依赖锁死控制流和安全行为 |

---

## 四、逐层讲解

### 4.1 数据层：真源与派生库

**设计原则（背下来）：CSV/Markdown 是可审计的"真源"，SQLite/Milvus 是脚本生成的"派生查询库"。改数据只改真源，然后重跑 `prepare_data.py`，永远不手改 shop.db。**

#### 订单：CSV → SQLite（`sql_store.py:37-136`）

- CSV 用 `days_ago`（相对天数）而不是绝对日期，导入时 `today - timedelta(days=days_ago)` 转成真实日期（`sql_store.py:85`）。**目的：课程例子"最近 30 天"永远不会因为时间流逝而过期。**这是做 demo 数据的通用技巧。
- 导入前逐行校验：`days_ago` 0~3650、`amount` ≥ 0、`order_id` 匹配 `^O\d{7}$`、`user_id` 匹配 `^U\d{4}$`、`status` 在白名单里。**脏数据在入口就炸掉（带行号报错），不让它进库。**
- 有效订单 = `paid/shipped/completed`；`cancelled/refunded` 不进统计。

#### 政策：Markdown → Milvus（`prepare_data.py:12-45` + `milvus_store.py`）

- 每份文档头部两行受控元数据：`政策类型：return_policy`、`适用类目：all`。缺了直接报错拒绝入库。
- 切分策略：`re.split(r"(?=^## )", text, flags=re.MULTILINE)` —— 按**二级标题**切 Chunk。`(?=...)` 是**零宽先行断言**：在 `## ` 前面"切一刀"但不吃掉标题本身，所以每个 Chunk 都带着自己的标题，保留章节语义。对政策类文档，**结构化切分优于固定字数切分**（不会把一条规则拦腰截断）。
- Milvus Collection Schema（`milvus_store.py:52-89`）：content/source/doc_type/chunk_index/policy_type/category/metadata + 向量字段。建了**两个索引**：向量字段 HNSW（COSINE 度量），`policy_type` 字段 INVERTED 倒排索引——后者就是"标量过滤"能高效执行的原因。
- 向量维度必须与 Embedding Provider 一致（`dim=self.embeddings.dimension`），所以**换 Embedding 模型必须重建 Collection 重新灌数据**，不同模型的向量空间不通用。

#### Embedding 的取巧设计（`embeddings.py`）

`HashEmbeddingProvider`：把文本拆成 字符+二元组+词 三种特征，每个特征用 blake2b 稳定哈希映射到 256 维向量的某一格并加减 1，最后单位化。**没有任何语义理解**，本质是个"字符级词袋指纹"，但：确定性（同一文本永远同一向量）、零依赖、够让"耳机退货"和退货政策文本产生非零相似度。**它存在的意义是让课程和自动化测试不依赖模型下载/API**，生产换 `sentence_transformers`。

### 4.2 Schemas：结构化决策的载体（`schemas.py`）

核心思想（上一课工程约束第一条）：**模块之间只传结构化对象，不传自由文本**。逐个看：

- `RouteName(StrEnum)`：七个路由值。用 `StrEnum`（Python 3.11+）的好处：成员本身就是字符串，`RouteName.SQL_QUERY == "sql_query"` 为 True，序列化/日志天然友好。**这是白名单：Executor 只认识这七个值，模型编造不出第八种工具。**
- `RouteDecision`：路由结果。关键字段：`routes` 是**列表**（复合意图多路由）、`requires_decomposition`、`filters`（提取的槽位）、`max_rounds`（预算随身携带）、`reason_code`（机器可读的决策原因，可观测性）。
- `PlanStep` / `RetrievalPlan`：执行计划。`PlanStep` 有 `id/tool/query/arguments/depends_on`。本项目 `depends_on` 恒为空（全是无依赖读任务），但字段留着——将来做依赖 DAG 不用改 Schema。
- `Evidence`：三个源的结果**统一格式**：`source_type`（milvus/sql/web）+ `source` + `content` + `score` + `metadata`。**这是整个系统的"通用货币"**——Grader 按它评分，答案按它引用，citations 按它返回。
- `ToolResult`：工具执行的**控制流信息**：status（success/empty/error）、latency_ms、retryable、error_code。**注意 Evidence 和 ToolResult 分开：一个给答案用，一个给控制流用**（`graph.py:126` 注释原话）。
- `QualityGrade`：评分结果，`recommended_action` 只能是 accept / rewrite_query / stop 三个动作之一。
- `QueryRequest/QueryResponse`：API 边界。`debug=false` 时 `executed_queries` 和 `trace` 不返回（不向普通用户暴露内部规划）。

**Python 点：`Field(default_factory=list)`**——可变默认值必须用工厂函数。写 `routes: list = []` 的话，所有实例会共享同一个列表（Python 经典坑）；`default_factory=list` 每个实例各造一个新列表。

### 4.3 DecisionEngine：大脑（`decision_engine.py`）

#### 接口先行：Protocol

```python
class DecisionEngine(Protocol):
    def route(...) -> RouteDecision: ...
    def plan(...) -> RetrievalPlan: ...
    def grade(...) -> QualityGrade: ...
    def rewrite(...) -> str: ...
    def answer(...) -> str: ...
```

**Python 点：`Protocol`（结构化子类型/"静态鸭子类型"）**。与 ABC 继承的区别：实现类**不需要**写 `class DemoDecisionEngine(DecisionEngine)`，只要方法签名对得上就算实现了协议。好处：
1. 解耦——`graph.py` 只依赖协议，不 import 任何具体引擎；
2. 测试友好——测试里随手写个 Fake 类就能注入，不用继承任何东西（`test_graph.py` 的 `FakeVectorStore` 同理）。
本项目四个协议：`DecisionEngine`、`VectorStore`、`WebSearchProvider`、`EmbeddingProvider`，全是同一个套路。

#### 槽位提取（`decision_engine.py:18-41`）

三个提取函数全是**确定性规则**，不是模型：
- `extract_user_id`：正则 `\bU\d{4}\b`（`\b` 词边界防止匹配到 "XU10015" 中段）。
- `extract_product_name`：`next((name for name in PRODUCT_NAMES if name.lower() in lowered), "")`——**生成器表达式 + `next` 带默认值**，找到第一个命中就停，找不到返回 `""`，等价于写 for 循环 + break 但一行搞定。
- `extract_policy_type`：关键词表匹配。

为什么槽位要确定性提取？课件红线：**"生产系统必须从登录态注入用户身份，不能让模型根据自然语言决定查谁的订单"**。课程里没有登录系统，就用正则模拟"受控注入"；DeepSeek 引擎里还会**用确定性结果覆盖模型输出**（`decision_engine.py:357-367`），模型说破天也改不了 user_id。

#### Demo 引擎的 route()：一条安全优先的决策链

顺序本身就是设计（`decision_engine.py:72-180`）：

1. **先拒绝**：敏感词（买家手机号/密码/支付密钥）→ REFUSE。**在任何数据访问之前**。
2. **再免检索**：改写/润色/翻译 → DIRECT_ANSWER。
3. **再查槽位**：要查订单但没有 user_id → CLARIFY（"我最近买了几单"走这里）。
4. **最后才选数据源**——注意这段：

```python
routes = []
if needs_docs: routes.append(RouteName.MILVUS_SEARCH)
if needs_sql:  routes.append(RouteName.SQL_QUERY)
if needs_web:  routes.append(RouteName.WEB_SEARCH)
```

**三个独立 if，不是 if/elif**。课件重点强调：elif 意味着"路由是单选题"，三源问题会只剩第一个命中的路由，双源/三源功能直接消失。**复合意图 = 路由是集合，不是标签。**

5. `len(routes) > 1` 时 `requires_decomposition=True` → 多源计划。

#### plan()：把路由翻译成可执行步骤

每个命中的路由生成一个 `PlanStep`。注意三个步骤的 query 不一样：Milvus/Web 直接用用户原话（语义检索要上下文），SQL 步骤**重新合成了一句结构化描述**（"统计用户 U1001 最近 30 天…"）——因为 SQL 工具根本不用 query 字段，真正的输入是 `arguments` 里校验过的 user_id/days/product_keyword，query 只是给 debug 输出看的。

#### grade()：确定性评分三步走

1. 按路由算出 `required_sources`（该有哪些源）；
2. 对比 Evidence 实际覆盖的 `available_sources`，差集 = missing；
3. Milvus 结果还要过 `min_evidence_score`（默认 0.35）分数门槛。

然后三分支：全齐且相关 → accept；缺但还有预算（`current_round < max_rounds`）→ rewrite_query；预算耗尽 → stop。
**注意它查不了语义缺口**（见甄别 3）——这是确定性 Grader 的天花板。

#### DeepSeek 引擎：换模型不换架构

`DeepSeekDecisionEngine(DemoDecisionEngine)` 继承 demo（plan/rewrite 直接复用），只覆写 route/grade/answer。四个关键设计：

1. **两个 LLM 客户端**：`self.llm`（答案用，Thinking 可开）和 `self.structured_llm`（路由/评分用，**Thinking 强制关**）。原因就是甄别 4 核实的那个 400 冲突：`with_structured_output(method="function_calling")` 会强制 tool_choice，而 V4 思考模式不接受强制 tool_choice。
2. **结构化输出直接绑 Pydantic 模型**：`with_structured_output(RouteDecision)` —— LangChain 把 Pydantic Schema 转成 function 定义发给模型，返回时自动校验成对象。模型输出不合 Schema 会重试/报错，**这就是"模型输出进图之前先过 Pydantic 校验"的落地**。
3. **None 兜底**：兼容接口可能返回普通文本导致结构化结果为 None，此时**回退到父类的确定性规则**（`super().route(...)`）。路由是关键控制决策，宁可用规则也不能空值继续。
4. **确定性覆盖模型槽位** + **SQL 无 user_id 强制 CLARIFY**：模型建议，程序把关。

> 这层的总纲：**"模型可以建议，程序才有决定权"**。route/grade 的输出都只是"建议"，预算、白名单、槽位校验全在程序层。

### 4.4 Graph：骨架（`graph.py`）

#### 结构：闭包工厂

```python
def build_graph(deps: GraphDependencies):
    def normalize_query(state): ...   # 这些节点函数都能看见 deps
    ...
    return builder.compile()
```

**Python 点：闭包**。所有节点函数定义在 `build_graph` 内部，自动捕获外层的 `deps`（引擎+三个工具+settings）。不用全局变量、不用给每个节点传参，测试时传不同的 `deps` 就得到行为不同的图。`GraphDependencies` 是个 `@dataclass`——纯数据袋子，比传五个散参数清爽。

#### 节点逐个过

| 节点 | 做什么 | 值得注意的点 |
| --- | --- | --- |
| `normalize_query` | 压空白归一化 | `" ".join(s.split())` 是压缩连续空白的惯用法 |
| `route_query` | 调 `engine.route()` | 决策进 state，trace 记 intent/routes/reason_code |
| `after_route`（条件边） | 决定去向 | **退出类优先**：CLARIFY > REFUSE > DIRECT > plan。模型要是返回了复合的怪路由，也先走退出，防止意外触发工具 |
| `plan_query` | 调 `engine.plan()` | 计划进 state |
| `execute_plan` | 执行全部步骤 | 单步直接跑；多步进 `ThreadPoolExecutor(max_workers=min(len,4))` 并行。`executor.map` **保持顺序**，所以后面能 `zip(steps, results, strict=True)` 一一配对（strict=True：长度不齐直接炸，防静默错位）|
| `grade_evidence` | 调 `engine.grade()` | **程序强制预算**：模型说 rewrite 但 `current_round >= max_rounds` 时，程序把动作改成 stop（`model_copy(update={...})`——Pydantic 不可变更新，产新对象不改旧的）|
| `after_grade`（条件边） | accept/rewrite/stop 三分支 | **只消费结构化动作字段，不解析 reason 自然语言** |
| `rewrite_query` | 改写 + 轮次+1 | 回到 plan_query 重新执行原计划 |
| `generate_answer` / `generate_partial_answer` | 生成完整/部分答案 | termination_reason 分别是 evidence_accepted / retrieval_budget_exhausted |
| `clarify` / `refuse` | 固定话术 | termination_reason = clarification_required / security_policy |

#### 三层防死循环（面试重点）

1. Grader 自身规则：预算耗尽返回 stop；
2. `grade_evidence` 节点：**无论模型说什么**，超预算强制 stop（测试 `test_graph_forces_stop_when_model_ignores_rewrite_budget` 专门用一个"永远要求 rewrite 的恶意引擎"锁死这个行为）；
3. LangGraph 兜底：`config={"recursion_limit": 20}`（`service.py:66`）。

轮次语义：`max_rounds=N` = 最多 N 次改写 = 最多 N+1 次执行。测试验证：max_rounds=1 时 vector store 被调用 2 次。

#### 为什么并行用线程池而不是 asyncio？

三个工具的 SDK（pymilvus、sqlite3、tavily 同步客户端）都是**同步阻塞**的，任务是 I/O 等待型。用 asyncio 得把整个调用链改成 async 或套 `run_in_executor`，还是线程池；直接 `ThreadPoolExecutor` 最简单。GIL 不碍事——线程在等 I/O，不抢 CPU。
课件提醒的边界：这个写法**只适用于无依赖读任务**。步骤有 `depends_on` 时要按拓扑排序分批执行，不能全丢进池子。

#### trace：追加不修改

```python
def trace_event(state, node, detail):
    return [*state.get("trace", []), {...}]   # 展开旧列表 + 新事件 = 新列表
```

每个节点返回**新的** trace 列表而不是往旧列表 append。LangGraph 的 state 更新按"返回的 partial dict 合并进状态"工作，返回新对象避免共享可变状态的隐性 bug。`[*a, b]` 是列表解包语法。

### 4.5 Tools：适配层（`tools.py`）

三个 Tool 类一个模式：**计时 → 调底层 → 成果转 ToolResult；异常也转 ToolResult，绝不往上抛**。

```python
except Exception as exc:
    return ToolResult(status="error", ..., retryable=True,
                      error_code="MILVUS_SEARCH_FAILED", error_message=str(exc))
```

- **Graph 不需要 try/except**——SDK 异常在适配层就被"驯化"成结构化数据了。一个工具挂掉不会炸掉整个图，Grader 看到该源缺证据自然会走 rewrite/stop。
- **错误分级**：`retryable=True`（网络类，重试可能好）vs `False`（参数被拒/没配 Key，重试也没用）。WebSearchTool 还区分了 `WEB_SEARCH_NOT_CONFIGURED`（RuntimeError，没 Key）和 `WEB_SEARCH_FAILED`（其他异常）——**except 子句从具体到宽泛排列**，Python 按顺序匹配第一个。
- `status="empty"`：查到 0 条不算 error 也不算 success——空结果是合法信号，交给 Grader 判断。
- **Python 点：`perf_counter()`** 测耗时（单调时钟，不受系统改时间影响），`time.time()` 是墙上时钟，测间隔要用前者。
- Tavily 的 `include_answer=False`：**搜索引擎自带的 AI 摘要不能当事实**，只收 title/url/content/score 自己组装 Evidence。

### 4.6 存储层的安全设计（本课的安全精髓）

#### SQL：固定模板 + 参数绑定（`sql_store.py:143-207`）

```python
sql = """SELECT ... FROM orders
         WHERE user_id = ? AND ordered_at >= ?
           AND status IN (?, ?, ?)
           AND (? = '' OR product_name LIKE ?)"""
row = connection.execute(sql, parameters).fetchone()
```

- 模型**永远不生成 SQL**，只能提供三个参数，且都先过校验：user_id 正则、days 1~365、keyword 长度 ≤100。
- `?` 占位符 = 参数化查询，用户输入永远是"数据"不会变成"代码"，SQL 注入从根上不存在。
- `AND (? = '' OR product_name LIKE ?)` 是**可选过滤的惯用技巧**：keyword 为空时第一个条件恒真，过滤自动失效；非空时走 LIKE。一条 SQL 覆盖两种情况。
- 我发现的一个小瑕疵（可当加分理解）：`product_keyword` 里如果含 `%` 或 `_`，会被 LIKE 当通配符。不是注入漏洞（跑不了任意 SQL），只是匹配范围会意外变宽。严格做法是转义 + `ESCAPE '\'` 子句。
- `COALESCE(SUM(amount), 0)`：没有匹配行时 SUM 返回 NULL，COALESCE 兜成 0。

#### Milvus：Filter 白名单（`milvus_store.py:122-125`）

```python
if policy_type and not policy_type.replace("_", "").isalnum():
    raise ValueError("policy_type 非法")
filter_expression = f'policy_type == "{policy_type}"' if policy_type else ""
```

Milvus 的 filter 是表达式语言，直接拼用户输入同样有注入风险。这里先做字符白名单（只允许字母数字下划线），再由程序拼出**唯一允许的表达式形状**。模型不能传任意 Milvus 表达式进来。

#### 凭证：SecretStr

`Settings` 里所有 key 都是 `SecretStr`：repr/日志/报错里自动显示 `**********`，只有显式 `.get_secret_value()` 才拿到真值（只在创建 SDK 客户端那一刻解密）。测试 `test_secret_values_are_masked_in_settings_repr` 锁死这个行为。

### 4.7 组装与入口

- `service.py`：**手工依赖注入**。构造函数接受可选的 `vector_store` / `web_search_provider`——测试传 Fake，生产传 None 走真实实现。`invoke()` 每次请求**新建完整初始 state**（评论原话：避免跨会话共享 Evidence）。
- `main.py`：FastAPI 两个端点 `/health`、`/query`。`@lru_cache(maxsize=1)` 把 `get_service()` 变成惰性单例——第一次调用才构建（连 Milvus 等重活），之后复用。`get_settings()` 同款。**Python 点：`lru_cache` 缓存的 key 是函数参数，无参函数=永远同一个 key=单例。**
- `cli.py`：`--debug` 先打印 executed_queries 再打印完整 JSON。开头那段 `sys.stdout.reconfigure(errors="backslashreplace")` 是 Windows 特供：GBK 控制台遇到 € 之类字符不会崩，转成转义序列输出。

---

## 五、测试解读

**这个项目的测试不是"跑一下没报错"，每个测试都在锁死一条架构承诺。**读测试=读需求。

| 测试 | 锁死的承诺 |
| --- | --- |
| `test_multi_source_route` | 双源问题路由必须同时含 MILVUS+SQL，槽位提取正确（if 不是 elif 的回归保险）|
| `test_three_source_route` | 三源路由 + requires_decomposition=True |
| `test_clarify_route` / `test_restricted_route` | 缺身份→CLARIFY；敏感请求→REFUSE，且 needs_retrieval=False |
| `test_clarification_does_not_call_vector_store` | **CLARIFY 时工具调用次数为 0**——"先拒绝后访问"不是嘴上说说，Fake 里有个 calls 计数器作证 |
| `test_multi_source_graph` | 端到端：路由→citations 含两种 source_type→trace 节点序列完全等于预期六步 |
| `test_empty_retrieval_stops_after_budget` | 空结果时：改写 1 次、共执行 2 次、termination=retrieval_budget_exhausted |
| `test_graph_forces_stop_when_model_ignores_rewrite_budget` | **恶意引擎每轮都要求 rewrite，程序层仍强制 stop**——三层防死循环的第 2 层 |
| `test_web_search_without_key_returns_isolated_error` | 没配 Key 只影响 web 工具自己（结构化 error），不炸系统 |
| `test_secret_values_are_masked_in_settings_repr` | 密钥不进日志 |
| `test_deepseek_structured_output_disables_thinking` | 用 monkeypatch 塞进假的 ChatOpenAI，断言两个客户端的 extra_body 一个 enabled 一个 disabled——**连"必须关 Thinking"这种坑都有回归测试** |
| `test_deepseek_grader_falls_back_when_structured_output_is_none` | LLM 结构化输出为 None 时回退确定性规则 |
| `test_parameterized_order_summary` | U1001 = 4 单 / 10396 元 / 低于99元 0 单（和课件数字互相印证）|
| `test_milvus_schema_insert_and_filtered_search` | Fake MilvusClient 断言：建了 HNSW+INVERTED 两个索引、向量 128 维、filter 表达式字符串精确等于 `policy_type == "return_policy"` |

测试策略分层：**单元测试全部用 Fake（不碰模型/网络/真 Milvus）测控制流；`scripts/smoke_test.py` 才连真实 Milvus+SQLite 验数据链路。**

两个值得学的测试技巧：
- **Fake + 计数器**：`FakeVectorStore.calls` 既当替身又当探针（验证"没被调用"这种否定性断言）。
- **monkeypatch**：`monkeypatch.setattr("app.service.create_decision_engine", lambda s: AlwaysRewriteDecisionEngine())` 临时替换工厂函数，测试结束自动还原；`monkeypatch.setitem(sys.modules, "langchain_openai", ...)` 甚至能伪造整个第三方模块（这样不装 langchain-openai 也能测 DeepSeek 引擎的构造逻辑）。
- `Settings(_env_file=None, ...)`：pydantic-settings 的隐藏参数，测试时禁止读真实 `.env`，保证测试环境隔离。

---

## 六、运行手册

```powershell
cd C:\workspace\Agentic_Rag

# 0. 先修 Bug：删掉 app/config.py 第 38 行末尾的 7

# 1.（可选）想先用无 Key 的确定性模式学习：把 .env 里 LLM_PROVIDER=deepseek 改成 demo

# 2. 环境（需要 Python 3.11 和 uv）
uv venv --python 3.11
uv sync --extra test              # 按需加 --extra deepseek --extra web

# 3. Milvus（二选一）
#   已有远程 Milvus：确认 .env 的 MILVUS_URI 可达
#   本地：docker compose -f infra/milvus/docker-compose.yml up -d
uv run python scripts/wait_for_milvus.py

# 4. 灌数据（CSV→SQLite；md→切分→向量→Milvus，可反复执行，全量重建）
uv run python scripts/prepare_data.py

# 5. 验收
uv run pytest                     # 单元测试，不碰网络
uv run python scripts/smoke_test.py   # 真实 Milvus+SQLite 冒烟

# 6. 玩
uv run python -m app.cli "统计 U1001 最近 30 天订单，并结合内部运费规则说明是否包邮" --debug
uv run uvicorn app.main:app --reload   # 然后 POST /query 或开 /docs
```

验收清单（对照课件第九节）：向量问题只打 Milvus；订单问题只打 SQLite、缺 user_id 澄清；双/三源生成对应数量并行步骤；debug 能看到真实 query/参数/状态/耗时；答案引用与 executed_queries 一致；循环有 max_rounds 和 termination_reason。

---

## 七、开发思维框架（以后自己做这类系统怎么想）

这是本课最值钱的部分：**不是记住这个项目，而是记住"下次从零做，按什么顺序想"**。八步法，每步有产出物：

### 第 1 步：先枚举问题类型，不是先选技术
产出：一张"问题类型 × 数据源 × 失败出口"表（就像本项目的七类问题表）。
- 每类问题标注：需要哪些源？缺什么槽位要澄清？什么请求直接拒绝？
- **失败出口和成功路径同等重要**——澄清、拒绝、部分答案、预算耗尽，一开始就要在表里。
- 判断值不值得上 Agentic：数据源单一、问题类型稳定 → 老老实实用固定 RAG（上一课的适用边界）。

### 第 2 步：定数据契约（Schema 先行）
产出：`schemas.py`。RouteDecision / PlanStep / Evidence / ToolResult / QualityGrade 这五个模型定义了模块间的全部对话方式。
- **Evidence 是通用货币**：不管几个源，先统一格式，下游（评分、生成、引用）就不用关心源的差异。
- 控制流数据（ToolResult）和内容数据（Evidence）分开。
- 动作字段用枚举/受控字符串（accept/rewrite_query/stop），**下游只 switch 动作，永远不解析自然语言**。

### 第 3 步：数据准备可重建
产出：真源文件（csv/md）+ 幂等的 prepare 脚本。
- 真源可审计、进 git；派生库（SQLite/向量库）随时可删可重建。
- 相对日期技巧（days_ago）让样例数据不过期。
- 入口校验，脏数据带行号报错，不入库。

### 第 4 步：大脑与骨架分离
产出：DecisionEngine 协议 + 图结构。
- **图（控制流）是固定的、可测试的；引擎（决策）是可替换的。**换模型 = 换引擎实现，图/工具/State 零改动。
- 先写确定性 demo 引擎再接 LLM：demo 引擎让你**没有 Key 也能开发和测试全部控制流**，还兼职当 LLM 失败时的 fallback。这个开发顺序值得抄。

### 第 5 步：工具 = 受控适配器
产出：每个数据源一个 Tool 类。
- 白名单参数 + 程序校验 + 模板化查询（SQL 模板 / Filter 白名单）。
- 异常在适配层转 ToolResult，图层不碰 SDK 异常。
- 错误分类：可重试/不可重试、未配置/真失败。

### 第 6 步：控制流有界
产出：预算参数 + 强制终止逻辑 + termination_reason 枚举。
- 模型建议 rewrite，程序决定还有没有预算；超了强制 stop。
- 图引擎层再加 recursion_limit 兜底。
- 每条结束路径都有明确的 termination_reason——这是可观测性也是验收标准。

### 第 7 步：可观测性内建
产出：trace 事件流 + executed_queries + latency + debug 开关。
- 每个节点记录"我是谁、什么时候、做了什么决策"。
- 实际执行的 query/参数/状态并列记录（计划 vs 实际）。
- debug 门控：内部轨迹不暴露给普通请求。

### 第 8 步：测试锁死承诺
产出：Fake 注入的控制流测试 + 真实依赖的 smoke。
- 每条安全红线配一个测试（不泄密、不越权、不死循环、不误触工具）。
- 用"恶意实现"（AlwaysRewriteEngine）测防御，不只测 happy path。
- 单元测试零网络零模型；真实链路只在 smoke 里。

### 安全清单（每一步都要过一遍）
1. 身份来自认证上下文，模型不能改（确定性覆盖）。
2. 查询语句程序生成，模型只给校验过的参数。
3. 退出类路由先于任何数据访问。
4. 网页内容是不可信文本，不能变成指令（提示注入防御）；搜索引擎的 AI 摘要不当事实。
5. 密钥只走 Settings/SecretStr，不进日志、trace、git。
6. 循环必有预算，预算由程序执行不由模型自觉。

---

## 八、课后作业实施指南

作业：企业 IT 故障诊断助手（阿里云 SSL-VPN 认证超时）。本质是**一次业务迁移**——架构不动，把"电商售后"换成"IT 故障诊断"。

### 迁移映射表（对着抄结构，别抄内容）

| 现有 | 作业里变成 | 要动的文件 |
| --- | --- | --- |
| `orders.csv`（days_ago/order_id/user_id/...） | `incidents.csv`（days_ago/incident_id/service_name/error_type/client_os/status/resolution） | `data/source/` 新文件 |
| `load_orders` 校验 + `summarize_recent` 订单统计 | `load_incidents` 校验 + `summarize_incidents`（按 service_name+error_type+时间窗统计次数、汇总 resolution） | `sql_store.py` 新增（或新建 incident_store.py）|
| 政策 md + `政策类型/适用类目` 元数据 | `vpn_troubleshooting.md` + `文档类型/服务名称/适用系统` 元数据 | `data/documents/` + `prepare_data.py` 的元数据解析 |
| Milvus 单过滤 `policy_type` | **双过滤 `service_name` + `client_os`** | `milvus_store.py`：Schema 加字段、search 的 filter 拼接要支持 AND（注意保持白名单校验！）|
| 槽位 user_id/product_name/policy_type | task_type/service_name/error_type/client_os/time_range | `decision_engine.py` 槽位提取 + 路由 |
| SQL_TERMS/DOC_TERMS/WEB_TERMS 关键词 | "几次/统计"→SQL；"怎么排查/手册"→Milvus；"公告/官网/服务异常"→Web | demo 引擎关键词表（想让 demo 模式也能跑通就得改）|
| web query=用户原话 | **受控 Query**：`site:help.aliyun.com/zh/vpn 阿里云 SSL-VPN 认证超时 运维事件 最新公告`（Planner 合成，不用原话）| `plan()` |
| Tavily 结果全收 | **域名白名单**：`urlparse(url).hostname == "help.aliyun.com"`，非官方结果丢弃 → 空 Evidence → Grader 给 partial | 新增过滤函数，接在 web evidence 后 |
| `FakeVectorStore/FakeWebSearchProvider` | `FakeVendorStatusProvider`（课件给了现成代码），走 `AgenticRAGService(settings, fake_store, fake_provider)` 第三参注入 | tests |

### 实施顺序（照第七节八步法走一遍）

1. 写 `incidents.csv`（4 条样例，INC1004 在 45 天前用于测时间窗）→ 导入校验 → 参数化统计查询 → **先写测试**：30 天窗口 = 3 次，INC1004 被排除。
2. 写 `vpn_troubleshooting.md`（按二级标题组织：常见原因/Windows 排查顺序/证书与 Profile 识别/升级条件）→ 元数据解析 → 入 Milvus → 双过滤检索测试。
3. 扩槽位提取和路由（缺服务名或现象 → CLARIFY）。
4. plan() 生成受控 web query；结果过域名白名单。
5. Grader 规则按课件那张五行表落地（重点：厂商证据缺失 → partial，答案不能排除公共服务异常；冲突 → 标记两条验证路径）。
6. 六个验收测试（对应课件 3.4/4 节）：① 30 天=3 次；② 只问次数→只打 SQL；③ 只问排查→只打 Milvus；④ 厂商证据缺失→partial；⑤ 首轮未召回→有限 rewrite；⑥ 三源齐→accept。全部用 Fake，不碰真网。

### 作业里最容易翻车的三个点

1. **Milvus 双过滤**：现在 `search()` 只接受 policy_type 一个过滤参数，你要扩展成能拼 `service_name == "..." and client_os == "..."`——记得每个值都过白名单校验再拼，别为了省事接受整条表达式字符串（那就把注入面开回来了）。
2. **别把用户原话当搜索词**：课件明确要求 Planner 合成受控 Query。用户原话里的"今天上午""频繁断开"对 site: 检索全是噪音。
3. **partial 的语义**：厂商证据缺失时，答案只能说"无法排除公共服务异常，建议先本地排查+关注官方公告"，不能说"是本地配置问题"。测试要断言答案不包含确定性根因表述。

---

## 九、Python 知识点汇总

按"这段代码在做什么/为什么这样设计"整理，入门语法跳过。

| 知识点 | 出现位置 | 一句话说透 |
| --- | --- | --- |
| `StrEnum`（3.11+） | `RouteName` | 枚举成员即字符串，比较/序列化零转换；同时充当工具名白名单 |
| `Protocol` | DecisionEngine 等 4 处 | "长得像就算实现"：不用继承即可替换实现，测试 Fake 随手写；靠 mypy/IDE 静态查签名 |
| `TypedDict, total=False` | `AgentState` | 给 dict 标注字段类型；total=False=字段可缺省，LangGraph 节点只返回自己改的那几个键 |
| `Field(default_factory=list)` | schemas | 可变默认值必须用工厂，否则所有实例共享同一个 list（经典坑）|
| `SecretStr` | Settings | repr/日志自动掩码，`.get_secret_value()` 才拿真值 |
| `field_validator(mode="after")` | config 路径解析 | Pydantic v2 校验钩子：字段解析完再加工（相对路径→绝对路径）|
| `model_copy(update={...})` | grade 强制 stop | Pydantic 不可变更新：产新对象不动旧的 |
| `with_structured_output(Model)` | DeepSeek 引擎 | LangChain 把 Pydantic Schema 变成 function calling 定义，返回自动校验成对象 |
| 闭包 | `build_graph` 内的节点函数 | 内层函数捕获外层变量 `deps`；工厂模式注入依赖，测试可换 |
| `@dataclass` / `frozen=True` | GraphDependencies / IndexedDocument | 纯数据袋子；frozen=不可变（可哈希、防误改）|
| `@lru_cache(maxsize=1)` | get_settings / get_service | 无参函数缓存 = 惰性单例 |
| `ThreadPoolExecutor` + `map` | execute_plan | 同步阻塞 I/O 的最简并行；map 保持输入顺序 |
| `zip(a, b, strict=True)`（3.10+） | 步骤×结果配对 | 长度不一致直接抛错，防静默错位 |
| 生成器表达式 + `next(gen, default)` | extract_product_name | 找第一个命中即停，找不到给默认值 |
| 字典/列表推导 + 条件过滤 | filters 构造、evidence 扁平化 | `{k:v for ... if v}` 只留非空槽位；双重 for 推导展平嵌套列表 |
| `re`：`\b`、`fullmatch` vs `search`、`(?=^## )` + MULTILINE | 槽位提取/入库校验/文档切分 | 词边界防误匹配；fullmatch 全串匹配做校验；零宽先行断言"切割但不吃掉分隔符" |
| `csv.DictReader` + `utf-8-sig` | load_orders | 按表头名取列；utf-8-sig 吃掉 Windows Excel 的 BOM |
| sqlite3：`?` 占位符 / `executescript` / `executemany` / `row_factory=Row` | sql_store | 参数化防注入；建表跑多语句；批量插入；按列名取值 |
| `Path(__file__).resolve().parents[1]` | config | 用源码位置定位项目根，不依赖启动目录 |
| `perf_counter` | tools 计时 | 单调时钟测间隔；time.time 是墙钟会被调整 |
| `Literal["a", "b"]` 返回类型 | 条件边函数 | 类型层面声明"只能返回这几个值"，LangGraph 用它对应边映射 |
| except 从具体到宽泛 | WebSearchTool | RuntimeError（没配 Key）和 Exception（真失败）给不同 error_code |
| `from __future__ import annotations` | 所有文件头 | 注解延迟求值：前向引用/新语法注解在旧运行时也不报错，还省运行时开销 |
| `monkeypatch.setattr/setitem(sys.modules, ...)` | 测试 | 临时替换属性甚至伪造整个模块，测试结束自动还原 |
| `sys.stdout.reconfigure(errors=...)` | cli | Windows GBK 控制台防崩：不可编码字符转义输出 |

---

## 十、自测题

学完合上笔记做一遍，答案在最后。

1. "统计 U1001 最近 30 天订单，并结合内部运费规则说明是否包邮"——demo 引擎下：路由是什么？生成几个 PlanStep？它们怎么执行？
2. 路由判断为什么必须用三个独立 if 而不是 if/elif？
3. Evidence 和 ToolResult 都描述工具结果，为什么要分成两个模型？
4. `max_rounds=2` 时，工具最多会被执行几轮？三层防死循环分别是什么？
5. 模型建议 `rewrite_query` 但预算已耗尽，系统在哪里、怎么处理？
6. 为什么 DeepSeek 引擎要建两个 LLM 客户端？（提示：Thinking 与 tool_choice）
7. SQL 工具的输入是什么？为什么说它天然免疫 SQL 注入？`(? = '' OR product_name LIKE ?)` 是干什么的？
8. Milvus 检索时模型能不能传一个自己写的 filter 表达式？代码里是怎么防的？
9. demo 引擎的 Grader 能不能识别"订单配送到哪里"这种问题的证据缺口？为什么？
10. "我最近 30 天买了几单"会发生什么？系统怎么保证这种情况下一个工具都不会被调用？
11. 换 Embedding 模型后为什么必须重建 Milvus Collection？
12. 测试为什么全部用 Fake 依赖？`FakeVectorStore.calls` 计数器是用来断言什么的？

<details>
<summary>参考答案</summary>

1. 路由 `[MILVUS_SEARCH, SQL_QUERY]`（"运费/包邮/规则"命中 DOC_TERMS，"统计/订单/最近"命中 SQL_TERMS），`requires_decomposition=True`；两个 PlanStep（search_policy: policy_type=shipping_policy, top_k=4；query_statistics: U1001/30 天/无商品关键词）；无依赖 → ThreadPoolExecutor 并行。
2. 路由是"集合"不是"单选"：elif 只保留第一个命中路由，双源/三源问题会退化成单源，复合问题拿不到完整证据。
3. ToolResult 是控制流数据（状态/错误码/耗时/可否重试），给 Grader 和错误处理用；Evidence 是内容数据（可引用的证据），给评分、答案生成和 citations 用。混在一起会让"答案引用"依赖工具内部细节。
4. 最多 3 轮（初始 1 + 改写 2）。三层：Grader 规则自身到预算返回 stop；grade_evidence 节点无视模型建议强制 stop；LangGraph recursion_limit=20 兜底。
5. 在 `grade_evidence` 节点（graph.py:179-192）：`current_round >= max_rounds` 时用 `model_copy(update=...)` 把动作改成 stop，走 generate_partial_answer，termination_reason=retrieval_budget_exhausted。
6. 答案生成可以开 Thinking（质量优先，.env 可控）；路由/评分用 `with_structured_output(function_calling)` 会强制 tool_choice，DeepSeek V4 Thinking 模式对强制 tool_choice 直接 400，所以结构化客户端必须固定关 Thinking。
7. 输入只有校验过的 user_id/days/product_keyword 三个参数；SQL 是固定模板+`?` 占位符，用户输入永远作为数据绑定、不参与 SQL 文本拼接。那个条件是"可选过滤"技巧：keyword 为空时条件恒真（不过滤），非空时按 LIKE 过滤。
8. 不能。policy_type 先过字符白名单（字母数字下划线），再由程序拼出唯一形状的表达式 `policy_type == "..."`；任何其他表达式形式都进不来。
9. 不能。demo Grader 只检查"要求的源是否都有 Evidence + Milvus 分数是否达标"。该问题在 demo 下只路由到 SQL，SQL 必有统计结果 → accept。语义级缺口（实时物流状态不在任何库里）只有 LLM Grader 或更多规则才能识别——这也是课件该案例实际依赖 DeepSeek 引擎的原因。
10. 命中 SQL_TERMS 但提取不到 user_id → route 直接返回 CLARIFY（在数据源选择之前）；after_route 条件边把 CLARIFY 排在最前面直通 clarify 节点 → END，根本不经过 plan/execute。测试用 Fake 的 calls==0 锁死。
11. 向量维度和语义空间由模型决定：维度不同 schema 都不兼容；就算维度相同，不同模型的向量空间也不可比，混用会得到无意义的相似度。
12. 单元测试要快、稳定、不依赖外部服务（模型/网络/Milvus），且能构造真实依赖很难复现的场景（空结果、恶意引擎）。calls 计数器用来断言"某些路径下工具没有被调用"（如 CLARIFY 时 calls==0）和"预算下的精确调用次数"（max_rounds=1 时 calls==2）。

</details>

---

## 附：本次核实的外部来源

- [DeepSeek V4 Preview Release（官方）](https://api-docs.deepseek.com/news/news260424/)：V4-Pro/V4-Flash 参数规模、1M 上下文、deepseek-chat/reasoner 退役时间
- [DeepSeek API Docs](https://api-docs.deepseek.com/)：`thinking: {"type": "enabled"/"disabled"}` 参数与 `extra_body` 用法
- [deepseek-ai/DeepSeek-V3 #1376](https://github.com/deepseek-ai/DeepSeek-V3/issues/1376)：Thinking 模式拒绝强制 tool_choice（400），影响 LangChain 等框架的结构化输出
- [pydantic/pydantic-ai #5193](https://github.com/pydantic/pydantic-ai/issues/5193)：同类问题的框架侧报告
- [OpenRouter: DeepSeek V4 Flash](https://openrouter.ai/deepseek/deepseek-v4-flash)、[Hugging Face: DeepSeek-V4-Flash](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash)：模型存在性旁证
