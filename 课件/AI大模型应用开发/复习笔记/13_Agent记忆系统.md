# Agent 记忆系统 复习笔记
> 对应课件：5.大模型 Agent 记忆系统设计五大范式.md

## 一、在知识体系中的位置

- **前置依赖**
  - **LangChain / LangGraph**：记忆系统最终要挂到 Agent 循环里用——什么时候读记忆、什么时候写记忆，都发生在 Agent 的推理循环（LangGraph 的节点/状态）中。
  - **RAG**：长期记忆的"检索"环节本质上就是 RAG 技术的复用——Embedding、向量库、BM25 关键词检索、混合检索、重排，全都在记忆系统里再次出现。区别只是检索对象从"外部文档"换成了"Agent 自己的历史"。
- **后续用途**
  - **A2A / Multi-Agent**：多 Agent 协作时，"谁能读写哪块记忆"是协作设计的核心问题（下一讲 Multi-Agent 编排会用到）。
  - **Agentic RAG**：让 Agent 自己决定"查不查、查什么、查几轮"——Letta 的 `archival_memory_search` 就是 Agentic RAG 思想在记忆场景的体现。

一句话定位：**记忆系统 = "RAG 技术 + 状态管理 + 数据治理"三者的交叉点**，是从"会聊天的 demo"走向"能长期服役的企业级 Agent"的必经一课。

## 二、核心知识点精讲

### 1. 为什么"接个向量库"不等于记忆系统

向量库只擅长一件事：**语义相似度匹配**（"用户喜欢什么风格"这类模糊问题）。但记忆系统面对的很多问题不是"相似"问题，而是"正确"问题：

- 问"我手机号多少"——需要的是**确定性读取**（像查通讯录），向量检索返回的是"长得像"的文本，不保证是对的那条；
- 用户上周说在上海、这周说在北京——两条记录在向量空间里**同时存在、互相矛盾**，检索时一起被召回，模型就会输出自相矛盾的答案。

所以课件给出四层参考分层（注意课件强调这是**参考**分层，不是必须四层全有）：

| 层级 | 存什么 | 类比 |
| --- | --- | --- |
| 会话状态 | 当前窗口、工具调用结果 | 桌面上正在看的文件 |
| 权威档案 | 偏好、身份、权限（精确读写） | 通讯录 |
| 任务摘要 | 目标、进度、待办 | 工作周报 |
| 历史检索 | 语义/关键词相关的历史片段 | 搜索引擎 |

**为什么要分层？** 因为不同数据的"读取正确性要求"不同：手机号错一位就是事故（必须走权威档案精确读），而"用户大概喜欢什么风格"错一点无伤大雅（可以走向量模糊召回）。把两类数据混进同一个向量库，等于用搜索引擎当通讯录用。

### 2. 记忆的三种认知类型（决定检索策略）

| 类型 | 存什么 | 检索策略 | 为什么 |
| --- | --- | --- | --- |
| 语义记忆 Semantic | 稳定事实、通用知识 | 向量检索 | 不绑定时间，按"意思"找最合适 |
| 情景记忆 Episodic | 具体事件、对话记录 | 时间线回溯 | "上次说了什么"关键在时间序，不在语义 |
| 程序记忆 Procedural | 验证过的操作流程 | 步骤回放 | 要的是"完整正确的流程"，不是碎片 |

**为什么必须区分？** 不区分就会出现课件里的经典事故：用户问"怎么部署"（要程序记忆），向量库却返回"上次部署失败了"（情景记忆）——语义上很相似，功能上完全没用。分类的意义在于：**先判断问题属于哪类记忆，再路由到对应的检索方式**。

课件注明这是"工程化分类"（借用认知科学术语，不是对人类记忆理论的完整复刻）。Mem0 把它与作用域（User/Session/Agent）正交组合成 3×3 矩阵；memU 的六种类型（Profile/Event/Knowledge/Behavior/Skill/Tool）是进一步细化。

### 3. Context Engineering：存 / 取 / 忘 三问

Anthropic 2025 年 9 月发表的《Effective context engineering for AI agents》把这个问题系统化了：上下文是**稀缺资源**，核心不是"写好提示词"，而是"每一步推理时，让窗口里恰好是最需要的那组 token"。落到记忆系统就是三问：

- **什么时候存**——什么都存 → 检索全是噪音；
- **什么时候取**——全量塞进上下文 → 模型分心（attention 被稀释）；
- **什么时候忘**——永不删除 → 旧信息污染新决策。

**记忆 vs 上下文的本质区别（本讲最重要的一张表）：**

|  | 记忆系统 | 上下文工程 |
| --- | --- | --- |
| 角色 | 长期仓库（存了什么） | 当前桌面（给模型看什么） |
| 风险 | 存太多→噪音；存太少→失忆 | 拿太多→分心；拿太少→失忆；拿错→越做越歪 |

> 仓库建得再好，桌上摆错了东西，模型照样犯错。

**Compaction（压缩）**：接近窗口上限时自动总结前文只留结论、清理旧工具结果、把摘要写入长期记忆。触发阈值要按模型窗口、任务风险、恢复成本设定，没有通用的固定比例。

### 4. 工作记忆：结构化摘要替代原始对话

几十轮任务后，不要保留全部原始对话，而是提取五要素结构化摘要：**用户目标 / 已完成步骤 / 关键结果 / 未解决问题 / 风险点**。这样 Agent 恢复状态时是"秒读周报"，不是"在几千行聊天记录里大海捞针"。Letta 的 Core Memory 就是这个理念的实现。

### 5. Ledger / Views / Policy：记忆的治理架构

生产级记忆要从"文本堆积"升级为"可治理的外部状态"：

- **Ledger（账本）**：只追加、可审计，像 Event Sourcing——记的不是"当前值"，而是"每一次变更事件"；
- **Views（视图）**：从账本**派生**出模型可读的当前状态（当前事实、任务进度）——账本是真相，视图可以随时重建；
- **Policy（策略）**：在 **LLM 外部**控制何时读、什么条件写、何时过期、敏感操作审批。

**为什么 Policy 必须在 LLM 外部？** 因为 LLM 会幻觉——如果让模型自己签发"我确认删除全部记忆"，防护就形同虚设。课件反复强调：Git/事件日志能提供"可追溯"，但**可追溯 ≠ 不可篡改**（有权限的人可以重写 Git 历史），高要求场景还需要签名或 WORM 存储。

### 6. 双时间机制（Bitemporal）

每条记忆两个时间戳：**Valid Time**（事实在现实中何时有效）+ **Transaction Time**（系统何时记录/失效它）。用户从上海搬到北京时，不是删掉旧记录，而是把上海记录标记"已失效"——检索时拿到的是"当前生效状态 + 清晰历史轨迹"，而不是两条打架的相似片段。这是数据库领域的成熟概念（bitemporal modeling），Zep 的知识图谱引擎 Graphiti 也采用了这种设计。

**关键提醒**："以新覆盖旧"只适用于来源可靠、语义明确的字段。对位置、偏好、诊断结论等可变信息，保留历史+来源+置信度+有效期，并允许"尚未判定"状态，比直接覆写更安全。

### 7. 五大范式各自解决什么问题

| 范式 | 一句话定位 | 核心机制 |
| --- | --- | --- |
| **Text2Mem** | 定义操作语言（自研接口的设计起点） | 12 个原子操作的 IR 中间表示；五元组 JSON 契约；dry_run/confirmation 安全字段；两层校验（结构+业务）+外部授权 |
| **Mem0** | 集成导向的中间件（接入最快） | 写入管线：提取→冲突消解→存储；多信号融合检索（向量+BM25+实体）；User/Session/Agent 三作用域 |
| **Letta** | 有状态 Agent 平台（Agent 自主管理记忆） | 虚拟内存隐喻：Core（窗口内，Agent 可编辑）/ Archival（外存，主动归档需显式搜索）/ Recall（外存，自动记录对话原文）；Sleeptime 后台反思 |
| **ReMe** | 文件即记忆（透明可审阅） | Markdown 文件是真源，索引是可重建的派生层；人可以直接打开审阅 |
| **memU** | 主动式记忆管线 | 双 Agent 异步：前台对话 + 后台 6 步记忆管线（活动记录→意图推断→更新建议→分类调整→关联→聚类演化） |

几个"为什么"级别的要点：

- **Text2Mem 的 12 操作分三阶段**：ENC 编码（Encode）｜STO 存储（Update/Label/Promote/Demote/Merge/Split/Delete/Lock/Expire）｜RET 检索（Retrieve/Summarize）。把 Retrieve 和 Summarize 拆开，是为了能**分别**设置缓存、超时、降级和成本预算——一个是毫秒级查库，一个是秒级模型生成，混在一起没法治理。
- **`confirmation` 字段的铁律**：不能由生成 IR 的同一次 LLM 调用置为 true，必须由外部授权服务/人工/独立校验流程签发——否则等于"让小偷自己开收据"。
- **Letta 三层的区别记忆法**：谁写入、写什么——Core 存精简摘要（Agent 主动编辑）、Archival 存提炼知识（Agent 主动归档）、Recall 存对话原文（系统自动记录）。类比：工作台便签 / 档案柜 / 监控录像。
- **Letta Sleeptime**：前台 Agent 追求低延迟；后台 Agent 每隔 N 轮用更大 Token 预算"慢思考"，把反思结果写回 Core Memory。对应 Letta 2025 年 4 月的论文《Sleep-time Compute》。
- **memU 检索哲学**：传统 RAG"给你一堆碎片拼图"（切块丢上下文），memU"给你整理好的笔记本、翻到相关章节让你自己判断"（检索只做粗筛，LLM 在聚焦后的完整文件里判断）。
- **ReMe 的一致性纪律**：文件删了，索引和向量必须同步删；Embedding 模型换了，向量索引必须重建——"文件真源 + 派生索引"架构的代价就是要维护一致性。

### 8. 治理边界（准确之外，还要可控）

五问最低要求：谁能读写（按用户/租户/Agent 分权）｜为什么写入（来源、置信度、用户同意；推断不得伪装成用户事实）｜保存多久（分类 TTL）｜如何纠错（版本+用户可查/改/删）｜如何主动行动（默认关闭推送，设预算和频率上限）。选型口诀：**没有银弹，先明确场景，再选范式**。

## 三、课件勘误与更新

总体评价：这版课件写作纪律很好——大量使用"以目标版本为准""接口形状示意""需核对"等限定语，把易过期的数字全部改成了"待核验"。以下是核实后的结果：

**1. Letta 代码示例使用已废弃的旧客户端 API**

- 课件原文：`from letta import create_client` / `client.create_agent(...)` / `agent.send(...)`（第三章代码实战，课件已自注"接口形状示意，不保证可直接运行"）
- 问题类型：**已过时**
- 正确/最新说法：旧版 `letta.client`（含 `create_client()`）已被官方标记废弃。现行 SDK 为独立包 `letta-client`：`from letta_client import Letta; client = Letta(base_url=... 或 api_key=...)`，创建 Agent 用 `client.agents.create(model=..., memory_blocks=[...], tools=[...])`，发消息用 `client.agents.messages.create(agent_id=..., ...)`。另外 `core_memory_append/core_memory_replace` 等经典工具名主要对应 legacy 的 `memgpt_agent` 类型，新版 agent 类型已转向 `memory_insert / memory_replace / memory_rethink` 等新工具名。
- 来源：https://github.com/letta-ai/letta-python ｜ https://docs.letta.com/api/python ｜ https://docs.letta.com/guides/legacy/memgpt_agents_legacy

**2. "MemR3 常作为对比基线"的说法与事实相反**

- 课件原文：脚注"² MemR3：基于 RAG 的记忆检索增强框架，在 LoCoMo 基准上常作为对比基线"
- 问题类型：**不严谨**
- 正确/最新说法：MemR³（Memory Retrieval via Reflective Reasoning，arXiv 2512.20237，2025 年 12 月）是一个**新提出的方法**，它在 LoCoMo 上**把别人当基线**（对比 Mem0、LangMem、A-Mem、Zep、vanilla RAG 等），而不是"常被别人当基线"。它也不是简单的"基于 RAG 的增强框架"，而是一个在 retrieve/reflect/answer 三个动作间做决策的闭环检索控制器。
- 来源：https://arxiv.org/abs/2512.20237

**3. "Anthropic 在 2025 年提出 Context Engineering"表述不够精确**

- 课件原文："Anthropic 在 2025 年提出了一个关键理念——Context Engineering（上下文工程）"
- 问题类型：**不严谨**
- 正确/最新说法：Context Engineering 一词在 2025 年上半年已由社区（Karpathy 等）和 LangChain 等厂商广泛使用；Anthropic 于 2025-09-29 发表《Effective context engineering for AI agents》，是**系统化阐述**这一理念的代表作之一，说"提出"容易让人误以为是 Anthropic 首创该词。课件归纳的"存/取/忘三问"是课件自己的提炼框架，Anthropic 原文的组织方式是 system prompt / 工具 / 压缩（compaction）/ 结构化笔记（memory）/ 子 Agent 等策略。
- 来源：https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents ｜ https://www.langchain.com/blog/context-engineering-for-agents

**4. ReMe 仓库归属已变更（补充信息）**

- 课件原文：项目卡片只写了 `reme-ai[core]>=0.4,<0.5`，未给仓库地址
- 问题类型：**已过时（信息补充）**
- 正确/最新说法：ReMe 前身是 MemoryScope，原仓库 modelscope/ReMe，现已迁至 agentscope-ai/ReMe；PyPI 包名 `reme-ai` 无误。其"文件+混合检索（wikilinks + BM25 + Embedding）"定位与课件描述一致。
- 来源：https://github.com/agentscope-ai/ReMe ｜ https://pypi.org/project/reme-ai/

**5. memU 的 PyPI 包名（补充信息）**

- 课件原文：安装命令处写"按官方文档安装并锁定目标版本；不要假定 PyPI 包名"
- 问题类型：**不严谨（课件已自我提示，此处补齐事实）**
- 正确/最新说法：memU 官方 Python 包名为 `memu-py`（`pip install memu-py`，要求 Python 3.13+），导入路径 `from memu.app import MemoryService`（新版 README 也展示 `from memu import MemoryService`）。课件的 `MemoryService` / `memorize()` / `retrieve()` API 形状与官方一致。
- 来源：https://github.com/NevaMind-AI/memU ｜ https://pypi.org/project/memu-py/

**以下课件内容经核实无误（增强信心用）：**

- Text2Mem 确有其paper：《Text2Mem: A Unified Memory Operation Language for Memory Operating System》（arXiv 2509.11145，MemTensor/text2mem，MIT 协议），12 个操作清单与课件完全一致（Encode；Update/Label/Promote/Demote/Merge/Split/Delete/Lock/Expire；Retrieve/Summarize），确实是"设计提案+基准"而非生产框架——课件的谨慎定位是对的。https://arxiv.org/abs/2509.11145 ｜ https://github.com/MemTensor/text2mem
- Letta Sleeptime Agent 真实存在：论文《Sleep-time Compute: Beyond Inference Scaling at Test-time》（arXiv 2504.13171），产品侧自 Letta 0.7.0 起提供 sleep-time agents（与主 Agent 共享 memory blocks、后台异步改写记忆）。课件"前台低延迟+后台大预算慢思考"的描述准确。https://arxiv.org/abs/2504.13171 ｜ https://docs.letta.com/guides/agents/architectures/sleeptime/
- Mem0 代码示例与现行 API 相符：托管版 `MemoryClient.add/search(query, user_id=...)`；开源版 `Memory.search(query, filters={"user_id": ...}, top_k=...)` 正是当前 v2.x 推荐写法（旧写法是顶层 `user_id=` + `limit=`）。https://github.com/mem0ai/mem0 ｜ https://docs.mem0.ai/core-concepts/memory-operations/search
- Mem0 CLI 真实存在：`npm install -g @mem0/cli`（或 `pip install mem0-cli`），命令形态 `mem0 init / add / search` 与课件一致。https://github.com/mem0ai/mem0/tree/main/cli ｜ https://www.jsdelivr.com/package/npm/@mem0/cli
- 三个基准都真实存在：LoCoMo（Maharana et al. 2024，50 段最长 35 session 的长对话）、LongMemEval（arXiv 2410.10813，五类记忆任务）、HaluMem（arXiv 2511.03506，MemTensor 出品，首个"操作级"记忆幻觉基准，评测对象包含 Mem0/MemOS/Zep 等）。课件"分数需核对版本与设置，不可横比"的态度正确。https://arxiv.org/abs/2410.10813 ｜ https://arxiv.org/abs/2511.03506 ｜ https://github.com/MemTensor/HaluMem
- Zep 脚注无误：github.com/getzep/zep，企业级记忆平台，其时间知识图谱引擎 Graphiti 正是双时间（bitemporal）建模的现实案例。

### 待核实

1. **配套实战项目仓库**（git.miaoatech.cn/zeroleap/MemoryAgents.git）为私有/内网地址，无法公开核实其"Text2Mem/ReMe 已启用、Mem0/Letta/memU 未启用"的边界描述，以学员本地实际代码为准。
2. **reme-ai 0.4.1.0 的具体行为**（`auto_memory`/`reindex` Job 名称、默认空 `embedding_store` 时走 BM25 分支、`dream_cron` 等）：公开检索只能确认 0.3.x 系列的发布记录与 0.4.x 版本约束的存在，Job 级细节需在本地装包后以 `reme-ai` 源码为准。
3. **Mem0 "单次 LLM 调用完成增/改/删判断"**（配图 OCR 中的说法）：Mem0 论文（arXiv 2504.19413）描述的是"提取阶段+更新阶段"两段式管线，具体调用次数随版本实现变化；课件正文已用"无论实际调用次数是多少"对冲，图中说法不要背成结论。
4. **memU"六种记忆类型/6 步后台管线"的当前版本对应关系**：memU 迭代很快（README 多次改版），Profile/Event/Knowledge/Behavior/Skill/Tool 六分类与 6 步管线是否与你安装的版本一致，需对照当期 README。
5. **Letta"双存储（Git+PostgreSQL）"架构图**：课件已注明这是"可选架构"而非 Letta 默认能力，实际 Letta 用 PostgreSQL 存状态；"Git 做记忆账本"更多是设计参考，未见官方默认实现。

## 四、课件没讲透的关键点补充

**1. 短期记忆 vs 长期记忆的本质区别（课件用了但没点破）**

- **短期记忆 = 上下文管理**：它根本不是"存储"问题，而是"窗口内放什么"的问题。消息裁剪、摘要压缩、工具结果清理，操作对象都是**这一次请求要发给模型的 token 序列**。它天然免费（不需要外部设施）但天然易失（会话结束就没了）。
- **长期记忆 = 外部存储 + 检索**：本质是一个**写入-存储-召回**的数据系统，模型本身对它一无所知，必须靠工程代码在合适时机把内容"注入"上下文。所以长期记忆的所有难题（写什么、何时取、怎么过期）都是**数据工程问题，不是模型问题**。
- 两者的接口就是上下文窗口：长期记忆再丰富，最终也要被压缩成窗口里的几百 token。这就是课件"仓库 vs 桌面"比喻的底层含义。

**2. 记忆写入时机——课件列了"存什么"，没讲"何时写"的三种典型设计**

- **同步写（hot path）**：每轮对话后立即提取写入（Mem0 的 `add` 就是这种）。优点是即时可用，缺点是拖慢响应、写入质量受限于单次调用。
- **异步写（background）**：对话照常进行，后台任务批量提取（memU 后台管线、Letta Sleeptime）。优点是不阻塞、可用大预算慢思考，缺点是有"记忆延迟窗口"——刚说的话可能还没入库。
- **Agent 主动写（agentic）**：模型自己调用 `core_memory_replace` 这类工具决定写什么（Letta 路线）。优点是最灵活，缺点是需要工具权限治理，防止模型乱写。
- 实际系统常三者混用：会话状态同步、事实提取异步、关键结论 Agent 主动写。

**3. 记忆冲突更新为什么难（课件给了机制，没讲难点根源）**

- 难点一：**"新"不等于"对"**。用户口误、模型误提取、A 说的被记到 B 头上——"时间戳取新"会让一次错误发言覆盖长期正确的档案。所以要"来源可靠性加权"。
- 难点二：**冲突检测本身要理解语义**。"我在北京"和"我人在上海出差"冲突吗？取决于问的是常驻地还是当前位置。这就是为什么 HaluMem 发现：幻觉主要产生在**提取和更新阶段**，然后一路传播到问答阶段。
- 难点三：**删除是最危险的写操作**。物理删除会毁掉审计线索，所以成熟设计都是"标记失效"（双时间机制）而非删除——这也解释了 Ledger 为什么"只追加"。

**4. "记忆检索复用 RAG"的完整对应关系（建议对照 RAG 笔记复习）**

| RAG 概念 | 记忆系统里的对应物 |
| --- | --- |
| 文档切块 chunking | 记忆提取（把对话切成原子事实） |
| Embedding + 向量库 | 语义记忆检索 |
| BM25 / 混合检索 | Mem0 多信号融合、ReMe 的 BM25 分支 |
| 重排 rerank | 记忆评分 / 融合排序 |
| 元数据过滤 | 作用域过滤（user_id / session_id）——**这里升级成了安全边界**，过滤失效=数据泄露 |

最后一行是关键差异：RAG 里过滤错了是"答得不准"，记忆系统里过滤错了是"把 Alice 的隐私告诉了 Bob"。

**5. 为什么"程序记忆→Skill"是当下最热的方向**：把验证过的成功流程沉淀成可复用技能（memU 的 Skill 类型、ReMe 的 Task Memory、以及 Claude Code 等编码 Agent 的 Skills 机制），Agent 才能从"每次现想"进化为"调用已验证方法"，这是降低长任务方差最有效的手段之一——因为流程一旦验证过，执行它就不再依赖模型每一步都推理正确。

## 五、Python 随堂补基础

课件实战代码（Text2Mem 引擎）用到不少中级语法，逐个补齐：

**1. Pydantic BaseModel：带校验的数据类**（记忆 IR 的"合同"就靠它）

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int = 0        # 有默认值 = 可不传

u = User(name="alice")           # 自动类型校验
print(u.age)                     # 0
User(name="bob", age="很多")     # 报 ValidationError：age 必须是 int
```

**2. `Literal` 类型：把取值限制成枚举**（`stage` 只能是三个值之一）

```python
from typing import Literal
from pydantic import BaseModel

class Op(BaseModel):
    stage: Literal["ENC", "RET", "STO"]

Op(stage="ENC")   # 通过
Op(stage="XXX")   # 报错：不在允许列表里
```

**3. `@field_validator` / `@model_validator`：自定义校验规则**

```python
from pydantic import BaseModel, field_validator, model_validator

class Op(BaseModel):
    stage: str
    op: str

    @field_validator("op")          # 校验单个字段
    @classmethod
    def check_op(cls, v):
        if v not in {"Encode", "Retrieve"}:
            raise ValueError("非法操作")
        return v

    @model_validator(mode="after")  # 校验字段之间的关系
    def check_match(self):
        if self.stage == "ENC" and self.op != "Encode":
            raise ValueError("stage 与 op 不匹配")
        return self
```

**4. `ClassVar`：类级常量，不算实例字段**

```python
from typing import ClassVar
from pydantic import BaseModel

class Op(BaseModel):
    VALID: ClassVar[set[str]] = {"Encode"}   # 全类共享，Pydantic 不当作数据字段
    op: str
```

**5. `Field(default_factory=...)`：可变默认值的正确写法**

```python
from pydantic import BaseModel, Field

class Op(BaseModel):
    args: dict = Field(default_factory=dict)  # 每个实例一个新 dict
# 千万不要写 args: dict = {} 之外再共享——函数默认参数同理：
def bad(x, cache={}):  ...  # 反面教材：所有调用共享同一个 dict
```

**6. `getattr` 动态取方法：按操作名分发处理器**

```python
class Store:
    def _exec_encode(self): return "写入"
    def run(self, op_name):
        handler = getattr(self, f"_exec_{op_name.lower()}", None)
        return handler() if handler else "没有这个处理器"

Store().run("Encode")   # → "写入"
```

**7. 集合运算 `|=`：合并集合**

```python
all_ops = set()
all_ops |= {"Encode"}          # 并集赋值，等价 all_ops = all_ops | {...}
all_ops |= {"Retrieve", "Summarize"}
print(all_ops)                 # {'Encode', 'Retrieve', 'Summarize'}
```

**8. f-string 格式化：`{n:04d}` 补零**

```python
n = 7
print(f"mem_{n:04d}")   # mem_0007（4 位宽，不足补 0）
```

**9. `async` / `await` + `asyncio.run`：memU 示例的异步调用**

```python
import asyncio

async def fetch():            # async def 定义协程：调用它不执行，只返回协程对象
    await asyncio.sleep(1)    # await：在这里"让出"，等结果再继续
    return "done"

result = asyncio.run(fetch()) # 程序入口用 asyncio.run 启动事件循环
```

**10. 列表推导式 + 条件过滤：检索的最简实现**

```python
memories = [{"content": "喜欢Python"}, {"content": "在北京"}]
hits = [m for m in memories if "python" in m["content"].lower()]
print(hits)   # [{'content': '喜欢Python'}]
```

## 六、自测清单

**是什么：**
1. 记忆系统的四层参考分层是哪四层？各自的"类比物"是什么？
2. 语义/情景/程序三种记忆各自对应什么检索策略？
3. Text2Mem 的 12 个原子操作分哪三个阶段？五元组 JSON 的五个字段是什么？
4. Letta 的 Core / Archival / Recall 三层，分别是"谁写入、写什么"？
5. 双时间机制的两个时间戳分别叫什么、什么含义？

**为什么：**
6. 为什么"我的手机号多少"不能靠向量检索回答？
7. 为什么"记忆系统"和"上下文工程"是两件事？用"仓库/桌面"比喻解释存太多、拿太多、拿错三种失败模式。
8. 为什么 `confirmation: true` 不能由生成该操作的同一次 LLM 调用签发？
9. 为什么 Ledger 要"只追加"而不是原地更新？"可追溯"和"不可篡改"差在哪？
10. 用户问"怎么部署"，向量库返回"上次部署失败了"——用记忆类型理论解释这个事故。
11. 为什么 Mem0 写入管线不能简单执行"时间戳取新"？举一个新值反而错误的例子。

**什么时候用：**
12. 团队想给现有客服机器人最快加上记忆，先验证价值——五大范式选哪条路线？要重点验证什么？
13. 合规部门要求"每条记忆改动都能人工审阅"——选哪条路线？代价是什么（提示：一致性）？
14. 你的 Agent 要 7×24 主动帮用户整理信息——上线前必须配置哪四类开关/上限？
15. 什么信号出现时，说明该从"全量对话历史"升级到"结构化工作记忆+Compaction"？

## 七、动手小练习

**练习 1（约 25 分钟）：给最小记忆引擎补一个 `Expire` 处理器**

课件的 Text2Mem 实战只实现了 Encode/Update/Lock/Delete/Retrieve 五个操作。请在此基础上：
1. 给 `MemoryStore` 增加 `_exec_expire`：接受 `args={"ttl_days": 30}`，给记忆写入 `expire_at` 字段（用 `datetime.now() + timedelta(days=30)`）；
2. 修改 `_exec_retrieve`：过滤掉 `expire_at` 早于当前时间的记忆；
3. 验证：Encode 一条 → Expire 它（ttl_days=-1，制造已过期）→ Retrieve 应查不到它，但它仍在 `store.memories` 里（软过期，不是删除）。
体会点：**"忘记"是检索层行为，不必是存储层删除**——这正是 Ledger 思想的迷你版。

**练习 2（约 20 分钟）：手写双时间机制的最小模型**

用一个 `list[dict]` 存地址记录，每条含 `value / valid_from / valid_to（None 表示至今）`。实现两个函数：
1. `update_address(records, new_value, now)`：把当前生效记录的 `valid_to` 封口为 `now`，再追加新记录（不许删除旧记录）；
2. `current_address(records)` 和 `history(records)`：分别返回当前生效值和完整轨迹。
用"6-01 上海 → 6-10 北京"的课件例子跑通，打印结果应同时给出"当前：北京"和完整历史。体会点：为什么保留历史后，"上周说上海、这周说北京"不再是矛盾，而是轨迹。
