# RAG 搭建与全链路优化 复习笔记
> 对应课件：`3.RAG系统搭建实战.md`、`4.RAG全链路优化：多路召回、查询测优化、Reranker.md`

---

## 一、在知识体系中的位置

**前置依赖（学这一篇前必须先懂）**

- **06 笔记**：RAG 是什么、向量是什么、余弦相似度。本篇是把那些概念**落成 LangChain 代码**。
- **Python 中级语法**：类（class）、列表推导式、`|` 运算符（LCEL 管道）、装饰器不需要但线程池要懂一点。第五节会补。
- **LLM API 调用常识**：知道"调用一次模型 = 一次网络请求 = 花钱花时间"，这样才理解为什么多查询/HyDE/查询分解要谈"额外开销"。

**本篇讲了什么（两份课件的骨架）**

```
课件3：搭一条"能跑"的 RAG
  文档加载(Loader) → 数据清洗 → 文本分块(5种策略) → Embedding
  → 向量库(Chroma) → 检索器(Retriever) → Prompt拼接 → LLM生成

课件4：把 RAG 从"能用"调到"好用"
  Milvus生产级向量库 → Embedding选型(MTEB/维度/Matryoshka)
  → 语义切片(百分位数法) → 多路召回(BM25+向量+多查询)
  → 查询侧优化(重写/分解/澄清/HyDE) → Reranker精排 → RAGAS评估
```

**往后连到哪里**

```
本篇（RAG 全链路）
   └─→ 模块三：Agentic RAG
        课件4的 create_retriever_tool + create_agent 已经埋了伏笔——
        把"检索器"封装成 Agent 的一个"工具"，让 Agent 自主决定
        何时检索、检索几次、怎么改写。本篇的每个优化技巧
        （查询重写/分解/多路召回/精排）都会变成 Agent 手里的一件"武器"。
```

一句话定位：**这是模块二的"主课"。课件 3 教你搭骨架，课件 4 教你每个环节怎么调优。学通这一篇，你就有了一套"检索质量诊断与优化"的完整方法论。**

---

## 二、核心知识点精讲

### 1. 两阶段架构：索引（离线）vs 查询（在线）

```
【索引阶段·离线】跑一次：文档 → 清洗 → 分块 → 向量化 → 存库
【查询阶段·在线】每次问：问题 → 向量化 → 检索Top-K → 拼Prompt → 生成
```

**核心认知：检索质量的上限，由索引阶段决定。** 切分策略、嵌入模型、向量库选型，任何一个环节出问题，在线阶段再怎么调都补不回来。课件那句"分块策略决定了 RAG 质量的 70%"数字未必精确（见勘误），但方向是对的——**分块是索引阶段最容易做砸、又最影响效果的一环**。

### 2. 完整链路七步（课件 3 的主线，务必背下来）

```
加载(load) → 清洗(clean) → 分块(split) → 嵌入(embed)
→ 存储(store) → 检索(retrieve) → 生成(generate)
```

- **加载**：`PyMuPDFLoader` 读 PDF，每页返回一个 `Document`，有两个属性：`page_content`（正文）和 `metadata`（页码/文件名等）。
- **清洗**：PDF 解析常有乱换行、项目符号、页眉页脚。不洗直接用，检索会被噪声干扰。
- **分块**：见下条，重点中的重点。
- **嵌入 + 存储**：用 Embedding 模型把每块变向量，连同原文一起存进向量库。
- **检索**：把库封装成 `retriever`，`retriever.invoke(query)` 返回 Top-K 相关块。
- **生成**：把检索到的块拼成 `context`，套进 Prompt 模板，`chain = prompt | llm | parser` 一次调用出答案。

### 3. 分块（Chunking）——五种策略与权衡

两个必须理解的参数：
- **`chunk_size`**：每块最大字符/Token 数。太大→检索精度降、Prompt 塞不下；太小→上下文断裂、语义丢失。
- **`chunk_overlap`**：相邻块的重叠字符数，防止"一句话被切两半、两半都不完整"。经验值取 `chunk_size` 的 10%~20%。**`chunk_overlap=0` 是新手最常犯的错。**

| 策略 | 原理 | 优点 | 缺点 | 适用 |
| --- | --- | --- | --- | --- |
| 固定字符 `CharacterTextSplitter` | 按分隔符+字符数硬切 | 最简单最快 | 粗暴，易切断句子 | 快速原型、规整文本 |
| **递归字符 `RecursiveCharacterTextSplitter`** | 按分隔符优先级"剥洋葱"：段落→换行→句号→…→硬切 | 语义完整性好、通用 | 需调 separators/size | **大多数场景默认首选** |
| 语义 `SemanticChunker` | 用 Embedding 算相邻句相似度，"断崖"处切 | 每块=一个完整话题 | 慢（要调 Embedding） | 技术文档/合同/论文 |
| 文档结构 `MarkdownHeaderTextSplitter` | 按标题/章节切 | 保留原文逻辑结构 | 依赖格式质量 | Markdown/结构化 PDF |
| LLM 分块 | 让大模型判断哪切哪留 | 最智能 | 最贵最慢 | 高价值小规模数据 |

**新手路线：先用递归字符分块，效果不好再上语义分块。别一上来搞最复杂的。**

### 4. 语义切块的百分位数法（课件 4 的重点难点）

`SemanticChunker` 参数 `breakpoint_threshold_amount`（如 95）不是"相似度阈值 95%"，而是**百分位数**：取所有相邻句相似度里第 95 百分位作为门槛，只有相似度排在**最低那 5%**的位置才切。

**为什么用百分位而不是固定阈值？** 固定阈值（如"低于 0.6 就切"）对文档整体相似度分布极敏感——文档整体连贯就一刀都不切，整体跳跃就切得稀碎。百分位是"按排名切最差的 X%"，**不管文档整体水平高低，都能自适应地找到话题转变最剧烈的地方。** 就像考试按"倒数 5% 划线"而不是"低于 60 分划线"。

数值方向：**`amount` 越大 → 门槛越高 → 切得越少、每块越大（越粗）。** 默认 90，块太大（含多话题）就降到 80~85，太碎就升到 92~95。

**LangChain 的优化——局部最小值策略**：只用单一阈值会在话题过渡区产生大量碎片（0.88、0.85 这种中等值也被切）。所以实际实现是两步：①百分位阈值**粗筛**出候选断点；②在候选点附近找相似度的**局部最小值（真正的谷底）**才切。这样 9 个候选断点能收敛成 2 个真正的切分点。

### 5. 向量库与索引（HNSW / ANN）

传统数据库擅长"精确查询"，不擅长"找相似的"。向量库专门做 **ANN（近似最近邻）**——在海量向量里快速找"足够相似"的（牺牲一点精度换巨大的速度）。

| 向量库 | 定位 | 适用 |
| --- | --- | --- |
| ChromaDB | 嵌入式、Python 原生、轻量 | 快速原型、小规模 |
| FAISS | 库、纯内存、快 | 大规模离线检索 |
| Milvus | 分布式、云原生、可持久化、支持亿级 | 生产环境 |
| Weaviate | 云服务、自带向量化 | 全托管 |

关键配置：`{"hnsw:space": "cosine"}`（Chroma）/ `metric_type="COSINE"`（Milvus）指定用**余弦**算距离。`hnsw` 指的是 HNSW 索引（见第四节补充）。

### 6. Embedding 选型四维度（课件 4）

选模型看四个维度：**效果、速度、成本、部署方式**。具体抓手：
- **向量维度**：384~512 快但表达弱；**768~1024 性价比最优（工业界主流，推荐）**；1536~4096 精度高但存储/检索贵。
- **最大文本长度**：512 token 配小块切片；8192 token 才能做大块检索/整文档嵌入。
- **Matryoshka 自适应维度**：部分模型（OpenAI `text-embedding-3`、通义 `text-embedding-v3/v4`）支持"高维向量天然含低维信息"，取前 N 维即可降维，一套 Embedding 多套精度。
- **API vs 本地**：原型用 API（`text-embedding-v3`）快速跑通；生产考虑本地部署（数据不出域、长期成本低）。常见混合方案：Embedding 走 API，Reranker 部署本地 GPU。

评测基准 **MTEB**（Massive Text Embedding Benchmark）是权威榜，但**榜分高≠你的数据上好**，必须用自己的真实数据跑一轮命中率（Top-K 命中率 / MRR）再定。

### 7. 多路召回：为什么"两条腿走路"

单一检索各有盲区：

| 检索方式 | 强 | 弱 |
| --- | --- | --- |
| **向量检索（稠密）** | 懂语义，"苹果公司"能匹配"Apple Inc." | 对精确关键词、型号、编号不敏感 |
| **关键词检索 BM25（稀疏）** | 精确匹配、速度快 | 不懂同义词（"感冒"匹配不到"风寒"） |

**混合检索 `EnsembleRetriever`**：并行跑多个检索器，再用**加权 RRF（互惠排名融合）**把结果融合。注意课件对它的机制描述有误（见勘误）。

**BM25 三条打分规则**（图书管理员类比，理解调优）：
1. **词频饱和**：关键词出现越多越相关，但到一定程度"封顶"，不会无限加分（防注水）。
2. **文档长度归一化**：短文里提一次 > 长文里提一次，惩罚又长又水的文档。
3. **逆文档频率 IDF**：越稀有的词越重要（"无麸质"比"蛋糕"更能定位）。

### 8. 查询侧优化：问题本身才是瓶颈

前面都在优化"检索"和"切片"，但很多时候**用户的问题本身就模糊/口语化/信息不足**。四种技术：

| 策略 | 一句话 | 一个问题变几个 | 开销 |
| --- | --- | --- | --- |
| 查询重写 | 口语化 → 精准专业表述 | 1→1 | 1 次 LLM |
| 查询分解 | 复杂问题 → 多个子问题分别查 | 1→N（纵深） | N 次 LLM + N 次检索 |
| 查询澄清 | 信息不足就先反问，不硬答 | 1→0（先问清） | 1 次 LLM |
| HyDE | 先让 LLM 编一段"假设答案"，用它去检索 | 1→1 | 1 次 LLM |
| 多查询检索 | 一个问题 → 多个改写版本 | 1→N（平铺） | N 次检索 |

**HyDE 的核心洞察**：用户问题是"短问句"，知识库文档是"长段落"，两者在向量空间分布有天然差距。让 LLM 先编一段"看起来像文档的假设答案"，**这段假设答案在长度/用词/句式上更接近真实文档，它的向量自然更靠近目标文档**。代价是多一次 LLM 调用，且假设答案可能有幻觉（应对：与原始问题向量加权融合）。

**查询分解 vs 多查询检索的区别**（易混）：多查询是"同一问题的不同说法"（平铺、扩大召回覆盖面）；查询分解是"把一个复杂问题拆成几个独立子问题"（纵深、每个子问题各查各的再汇总）。

### 9. Reranker 精排：两阶段检索的"面试环节"

```
粗排（召回）：向量/BM25 快速捞 Top-20~100  →  速度快、精度粗（海选）
精排（重排）：Reranker 逐条精算相关性，重排选 Top-3  →  慢但准（面试）
```

**Reranker 和 Embedding 的本质区别（关键）**：
- **Embedding（双塔/bi-encoder）**：问题和文档**各自**压成一个向量，再算余弦。文档向量可**预先算好存库**，检索快；但把整段话压成一个向量**信息有损**。
- **Reranker（交叉编码/cross-encoder）**：把"问题+文档"**拼在一起**塞进模型，直接输出一个相关性分数。**信息无损、精度高**，但每个"问题-文档对"都要现算，**无法预存、慢**，所以只能对粗排后的少量候选（几十条）做精排。

课件用的是通义 `qwen3-rerank`（`dashscope.TextReRank.call`），这个模型名和用法**是正确的、当前有效的**。

### 10. RAGAS 评估四指标

没有量化评估，调参就是盲人摸象。RAGAS 用 LLM 当裁判，四个指标：

| 指标 | 管什么 | 原理 |
| --- | --- | --- |
| **Faithfulness 忠实度** | 防幻觉，答案有没有据 | 答案拆成陈述，看每条能否被上下文支撑 = 被支撑数/总数 |
| **Answer Relevancy 答案相关性** | 答案跑不跑题 | 让 LLM 从答案反推问题，与原问题算相似度 |
| **Context Precision 上下文精确度** | 检索排序好不好（相关的排前面没） | 类似 Precision@K |
| **Context Recall 上下文召回率** | 该找的信息找全了没 | 需标准答案，看标准答案的信息能否从上下文推出 |

前两个评"生成"质量，后两个评"检索"质量。**池化标注法**降标注成本：多个检索器各召回 Top-K 取并集成"候选池"，只标候选池而非全库。

---

## 三、课件勘误与更新

> 核查纪律：具体 API/类名/参数均已对照官方文档核实。LangChain 1.0（2025-10 发布）把大量旧 API 拆分/迁移，课件属于"部分已跟进 1.0、部分仍用旧写法"的混合状态，需逐条区分"错误"与"已过时"。

### 已确认勘误

| 课件原文 | 问题类型 | 正确/最新说法 | 来源 |
| --- | --- | --- | --- |
| （课件4 5.3/5.5）`EnsembleRetriever(retrievers=..., weights=[0.4,0.6], normalize_scores=True)`，注释"将不同检索器的分数归一化到[0,1]" | **错误** | `EnsembleRetriever` **没有 `normalize_scores` 参数**，传入会报 `TypeError`。它的真实机制是**加权互惠排名融合（weighted Reciprocal Rank Fusion, RRF）**——只用"排名"不用"原始分数"，根本不做分数归一化。真实参数是 `retrievers`、`weights`、`c`（RRF 常数，默认 60）、`id_key`。注释对机制的描述也是错的 | LangChain 官方参考 https://reference.langchain.com/python/langchain-classic/retrievers/ensemble/EnsembleRetriever |
| （课件3）`from langchain_community.vectorstores import Chroma` | 已过时 | 该导入自 LangChain 0.2 起弃用，会有 Deprecation 警告。现应 `pip install -U langchain-chroma` 后用 `from langchain_chroma import Chroma`。功能等价，非"错误"，但新项目应改 | LangChain Chroma 集成文档 https://python.langchain.com/docs/integrations/vectorstores/chroma/ |
| （课件4）`from langchain_community.vectorstores import Milvus` | 已过时 | 自 0.2.0 弃用，计划在 community 1.0 移除。现应 `pip install -U langchain-milvus`，用 `from langchain_milvus import Milvus`（或 `MilvusVectorStore`）。功能等价 | LangChain 迁移指南 https://docs.langchain.com/oss/python/migrate/langchain-v1 ；弃用说明 https://api.python.langchain.com/en/latest/vectorstores/langchain_community.vectorstores.milvus.Milvus.html |
| （课件3 3.1/3.2）正则 `re.compile(r'[^一](\n)[^一]', ...)`，注释"删除非中文字符之间的换行符" | **错误/不严谨** | `[^一]` 的字面含义是"除了汉字'一'以外的任意单个字符"，**并不表示"中文字符"**。代码与注释完全对不上，实际效果是"删除两侧都不是'一'字的换行符"，几乎等于无差别删换行，达不到"保护中文句内换行"的目的。若真想匹配中文，应写 `[一-龥]`（或 `一-鿿`）字符区间 | Python `re` 官方文档（字符集语义） https://docs.python.org/3/library/re.html |
| （课件3 5.2）Embedding 选型表 `text-embedding-v3` 维度列"1024/768" | 不严谨/已过时 | `text-embedding-v3` 实际支持 **1024(默认)/768/512/256/128/64** 六档，非只有两档；最大输入 8192 token。且截至 2026 年已有更新的 `text-embedding-v4`（支持到 2048 维）。课件4 表格里写的"1024 维/8192 长度"才是准确口径 | 阿里百炼向量化文档 https://help.aliyun.com/zh/model-studio/embedding |
| （课件4）第八章标题"第八章：RAG 效果评估体系"，其下小节却编号为 10.1/10.2/10.3/10.4 | 不严谨（编辑疏漏） | 章号与小节号不一致，应为 8.1/8.2/…。不影响内容正确性，仅排版错乱 | —（课件内部一致性问题，无需外部来源） |
| （课件3 4.1 & 9.1）"分块策略决定了 RAG 质量的 70%"、"chunk_size 一般 500-1000 字符" | 不严谨（无权威来源的具体数字） | "分块极重要"方向正确，但"70%"是营销式估算，无论文/官方支撑，宜理解为"强调重要性"而非精确结论。chunk_size 经验值本身合理，但应说明它强依赖 Embedding 模型的最大长度与业务文本特性 | 无权威来源可佐证具体百分比，按经验值理解即可 |

### 待核实

| 事项 | 说明 |
| --- | --- |
| （课件4 3.3）"BGE-M3 支持 Matryoshka 自适应维度"，及代码 `dense_256 = dense_vecs[:, :256]` "成本降低75%、精度损失<5%" | 官方 BGE-M3（BAAI，Chen et al. 2024）主打的是 dense/sparse/multi-vector 三合一，**其模型卡并未明确宣称用 MRL/Matryoshka 训练**；Matryoshka 是 BGE **v1.5** 系列与 OpenAI `text-embedding-3`、通义 `v3/v4` 的明确特性。对未经 MRL 训练的模型直接截断维度，质量损失可能远大于"<5%"。此条**存疑，建议以 BGE-M3 官方模型卡为准**（https://huggingface.co/BAAI/bge-m3），不宜照搬"取前256维几乎无损"的结论 |
| （课件4 2.3）Milvus `create_collection(..., metric_type="COSINE")` 与随后 `index_params.add_index(field_name="vector", index_type="AUTOINDEX")`（未在 add_index 里指定 metric_type） | 新版 pymilvus 中，显式 schema + 独立建索引的流程下，`metric_type` 通常应放在 `add_index(...)` 里；在 `create_collection` 层传 `metric_type` 是否对已显式建索引的字段生效，各版本行为不一。建议以你实际安装的 pymilvus 版本文档为准，安全做法是在 `add_index` 里显式写 `metric_type="COSINE"` |
| （课件4）注释"langchain_community 要使用 0.4.1 版本"、"langchain_experimental==0.4.1" | 具体版本号锁定与你本地其它包的兼容性相关，未逐一核验；按课件跑不通时以 `pip` 实际依赖解析报错为准 |
| （课件3）`DashScopeEmbeddings`、`ChatTongyi` 仍从 `langchain_community` 导入 | 这两个目前主要仍在 `langchain_community`，可能出现弃用提示但一般仍可用；是否已迁出到独立包未逐一核实，暂不列为勘误 |

---

## 四、课件没讲透的关键点补充

### 1. HNSW 索引到底是怎么"快"的

课件反复出现 `hnsw:space`，却没讲 HNSW 是什么。HNSW = Hierarchical Navigable Small World（分层可导航小世界图）。直觉：把所有向量连成一张"图"，分成多层——**上层稀疏、像高速公路，下层稠密、像小巷**。查询时先在高速公路上大跨步逼近目标区域，再逐层下沉到小巷精找。这样就不用和库里每个向量都比一遍（那是暴力检索 O(N)），而是走图上的少数几跳就到，速度接近 O(log N)。代价是"近似"——可能漏掉极个别真正最近的点，但这点误差换来的是几十上百倍的加速。这就是为什么向量库做的是 **ANN（近似）而非精确最近邻**。

### 2. BM25 与稠密检索为什么必须互补（这是多路召回的灵魂）

- **稠密（向量）检索**懂"意思"，但对**精确符号无能**：搜"特斯拉 Model Y 2024款 后轮驱动版报价"，它可能返回"Model 3 报价""Model Y 2023款"——因为语义都很近，但你要的是**精确那一款**。
- **BM25（稀疏/关键词）**死抠字面，对"2024款""后轮驱动"这种关键词精确命中，但完全不懂"感冒≈风寒"。

所以型号/编号/专有名词类查询靠 BM25 兜底，同义/改写类查询靠向量兜底，**两者的错误模式几乎正交**，融合后互相补盲区——这才是 `EnsembleRetriever` 存在的根本理由，而不是"多个总比一个好"这么笼统。

### 3. RRF（互惠排名融合）到底怎么算——课件回避了的核心

既然课件把 `EnsembleRetriever` 的机制讲错了，这里补正确的。RRF 只看**排名**不看**原始分数**（因为 BM25 的分数和余弦相似度根本不在一个量纲，直接相加没意义）。每个文档的融合得分：

$$
\text{score}(d)=\sum_{r\in\text{检索器}} w_r \cdot \frac{1}{c + \text{rank}_r(d)}
$$

其中 `rank` 是该文档在某个检索器结果里的名次（第 1 名 rank=1），`c` 是常数（默认 60，用来削弱头部名次的过大权重），`w` 是你给的权重。**关键点：它规避了"不同检索器分数无法直接比较"的难题——只比名次，天然可融合。** 这也解释了为什么课件那个 `normalize_scores` 参数不存在：RRF 压根不需要归一化分数。

### 4. `chunk_overlap` 为什么能救命——具体机制

不是"多留点总没坏处"这么模糊。想象一句关键信息"HDC 在 30~60km/h 激活"正好落在切分边界：无重叠时，块 A 结尾是"HDC 在 30~"，块 B 开头是"60km/h 激活"，**两块都不完整**，检索"HDC 激活速度"时哪块都匹配不全。设了 overlap，块 B 会往前多包含块 A 的尾巴，让"30~60km/h 激活"完整出现在块 B 里。所以 overlap 的本质是**用冗余存储换"关键信息不被边界劈开"的保险**。

### 5. Reranker 为什么"贵"却"准"——cross-encoder 的算力代价

第二节讲了 bi-encoder vs cross-encoder 的区别，补一句代价来源：bi-encoder 下 N 个文档只需 N 次编码（且可预存）；cross-encoder 要对"1 个问题 × N 个候选"做 N 次**完整的前向推理**（问题和文档拼一起过一遍模型），且**无法预存**（因为要等问题来了才能拼）。所以精排只能作用在粗排后的几十条上——**先用便宜的 Embedding 把 100 万篇缩到 50 篇，再用昂贵的 Reranker 把 50 篇精排到 3 篇**，这就是两阶段架构的经济学。

### 6. 查询侧优化和检索侧优化是"两个战场"

课件把它们混在一起讲，容易乱。理清楚：
- **检索侧优化**（切片、Embedding 选型、多路召回、Reranker）改的是"**怎么找**"。
- **查询侧优化**（重写、分解、澄清、HyDE）改的是"**拿什么去找**"——在检索**之前**先把用户的烂问题打磨好。

一个完整生产链路的推荐组合（课件末尾也提到）：**查询澄清（入口过滤）→ 查询重写（标准化）→ HyDE/多查询（扩展）→ 多路召回 → Reranker 精排 → 生成**。理解这条流水线，你就有了系统性的调优地图。

### 7. LCEL 的 `|` 到底在干嘛

课件反复写 `chain = prompt | llm | StrOutputParser()`，没解释。这个 `|` 是 LangChain 的 **LCEL（表达式语言）**，借用了 Python 的管道语义：**把上一个组件的输出，喂给下一个组件的输入**，像 Linux 管道 `cat file | grep x | wc`。`prompt | llm | parser` = "先用 prompt 拼好提示词 → 交给 llm 生成 → 再用 parser 把输出解析成纯字符串"。它本质是 Python 的运算符重载（`__or__`），第五节会讲原理。

---

## 五、Python 随堂补基础

本篇代码密集，挑最容易卡住的语法点，每个配极简示例。

### 1. f-string 里的格式化控制（到处在用）

```python
score = 0.87345
print(f"分数：{score:.4f}")   # 分数：0.8734  （.4f = 保留4位小数）
name, k = "块", 3
print(f"--- {name}{k} ---")   # --- 块3 ---
```

### 2. 列表推导式 + 条件过滤（分块后过滤空块的写法）

```python
docs = ["有内容", "", "  ", "又有内容"]
# 保留：非空 且 去掉首尾空格后仍非空
valid = [d for d in docs if d and d.strip()]
print(valid)   # ['有内容', '又有内容']
```
读法：`[表达式 for 变量 in 列表 if 条件]`。`d.strip()` 去首尾空白；空字符串在 `if` 里视为 False。

### 3. `lambda` 匿名函数（出现在 `re.sub` 的替换参数里）

```python
f = lambda x: x * 2        # 等价于 def f(x): return x*2
print(f(5))                # 10
# re.sub(pattern, 替换函数, text)：匹配到的每一处都调用这个函数
import re
print(re.sub(r'\d', lambda m: "#", "a1b2"))   # a#b#
```

### 4. 类（class）、`__init__`、`self`（课件的 RAG 系统都封装成类）

```python
class Retriever:
    def __init__(self, k):     # 构造函数，new 对象时自动调用
        self.k = k             # self.xxx = 把参数存进对象，供其它方法用
    def search(self, query):
        return f"用 top-{self.k} 检索：{query}"

r = Retriever(k=3)             # 触发 __init__
print(r.search("老师是谁"))    # 用 top-3 检索：老师是谁
```
`self` = "这个对象自己"，每个方法第一个参数都得写 `self`（调用时不用传）。

### 5. 字典做"分发表"（`search(mode)` 用 dict 选检索器）

```python
retriever_map = {"bm25": "A", "vector": "B", "ensemble": "C"}
mode = "vector"
if mode not in retriever_map:            # 先校验合法性
    raise ValueError(f"不支持：{mode}")
print(retriever_map[mode])               # B
```
比一长串 `if/elif` 更干净，是课件 `MultiRetrieverSystem.search` 的核心技巧。

### 6. `set` + `hash()` 去重（合并多路检索结果时用）

```python
seen = set()                 # 集合，天然去重、查成员 O(1)
result = []
for text in ["a", "b", "a", "c"]:
    h = hash(text)           # 把内容转成一个哈希整数当"指纹"
    if h not in seen:
        seen.add(h)
        result.append(text)
print(result)                # ['a', 'b', 'c']
```

### 7. `try / except` 兜底解析（解析 LLM 返回的 JSON 时防崩）

```python
import json
raw = 'LLM可能返回不规范内容'
try:
    data = json.loads(raw)   # 尝试把字符串解析成 Python 对象
except json.JSONDecodeError: # 解析失败就走兜底，不让程序崩
    data = raw.split("\n")   # 兜底：按行拆
print(data)
```

### 8. 线程池并行（查询分解后并行检索，`ThreadPoolExecutor`）

```python
from concurrent.futures import ThreadPoolExecutor

def work(x):
    return x * 10

with ThreadPoolExecutor(max_workers=3) as ex:   # 开3个线程
    futures = [ex.submit(work, i) for i in [1, 2, 3]]  # 提交任务
    results = [f.result() for f in futures]     # 收结果（会等它算完）
print(results)   # [10, 20, 30]
```
用途：3 个子问题同时检索，比一个个串行快。I/O 型任务（等网络）用线程池最合适。

### 9. `|` 运算符重载（LCEL 管道的原理，理解即可）

```python
class Step:
    def __init__(self, name): self.name = name
    def __or__(self, other):   # 定义 a | b 时会调用 a.__or__(b)
        return f"{self.name} → {other.name}"

print(Step("prompt") | Step("llm"))   # prompt → llm
```
LangChain 就是靠给组件定义 `__or__`，让 `prompt | llm | parser` 这种写法成立。你不用自己写，会读就行。

---

## 六、自测清单

**是什么（概念层）**
1. RAG 的索引阶段和查询阶段各做什么？哪个决定检索质量的上限？
2. `chunk_size` 和 `chunk_overlap` 分别是什么？`chunk_overlap=0` 会导致什么问题？
3. 五种分块策略分别叫什么？各自的适用场景？
4. 向量检索（稠密）和 BM25（稀疏）各自的强项和盲区是什么？
5. Reranker 和 Embedding 模型的本质区别是什么（双塔 vs 交叉编码）？
6. RAGAS 的四个指标分别评估什么？哪两个评检索、哪两个评生成？

**为什么（原理层）**
7. 为什么语义切块用"百分位数法"而不是"固定相似度阈值"？
8. 为什么 `EnsembleRetriever` 用 RRF（只看排名）而不是直接把两个检索器的分数相加？
9. HyDE 为什么能提升检索效果？它的核心洞察是什么？代价是什么？
10. 为什么 Reranker 只能对粗排后的少量候选做，而不能直接对全库做？
11. 为什么建库和查询必须用同一个 Embedding 模型？
12. 为什么向量库做的是 ANN（近似最近邻）而不是精确最近邻？HNSW 靠什么加速？

**什么时候用（应用层）**
13. 什么场景该用查询分解、什么场景该用多查询检索？两者区别？
14. 用户问"这个多少钱"，系统应该直接检索还是先做点别的？为什么？
15. 中文、数据不能出域的项目，Embedding 该怎么选？可以走 API 的呢？

---

## 七、动手小练习

### 练习 1（约 30 分钟）：对比递归分块 vs 语义分块

用一段 3~4 个不同话题的中文文本（比如各抄一段"天气""编程""美食"），分别用 `RecursiveCharacterTextSplitter`（`chunk_size=100, chunk_overlap=20`）和 `SemanticChunker`（`breakpoint_threshold_amount=90`）切，打印每种切法的块数和每块前 30 字。

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_experimental.text_splitter import SemanticChunker  # 需配 embedding

text = "（自己拼一段跨3个话题的文本）"
r = RecursiveCharacterTextSplitter(
    separators=["\n\n", "\n", "。", "！", "？", " ", ""],
    chunk_size=100, chunk_overlap=20, length_function=len,
)
for i, c in enumerate(r.split_text(text)):
    print(f"[递归 块{i+1}] {c[:30]}")
```
**目标**：亲眼看到递归分块会在"字数够了"的地方硬切（可能切在话题中间），而语义分块倾向在"话题切换处"切。体会两者的差异。（没有 Embedding key 时，可只跑递归分块，手动观察它在哪些地方切断了语义。）

### 练习 2（约 25 分钟）：给 `EnsembleRetriever` 纠错并跑通

拿课件 5.3 的代码，做两件事验证本篇勘误：
1. 原样保留 `normalize_scores=True` 跑一次，观察是否报 `TypeError`（确认这个参数不存在）。
2. 删掉 `normalize_scores=True`，改成合法写法（可加 `c=60` 试试），再跑通，打印 BM25、向量、混合三种模式各自返回的 Top 结果，对比同一个问题下三者召回的差异。

```python
# 伪代码骨架
bm25 = BM25Retriever.from_documents(docs); bm25.k = 5
vec = vectorstore.as_retriever(search_kwargs={"k": 5})
ensemble = EnsembleRetriever(retrievers=[bm25, vec], weights=[0.4, 0.6])  # 去掉 normalize_scores
q = "在多少速度范围内，HDC才会激活？"
print("BM25:", [d.page_content[:20] for d in bm25.invoke(q)])
print("向量:", [d.page_content[:20] for d in vec.invoke(q)])
print("混合:", [d.page_content[:20] for d in ensemble.invoke(q)])
```
**目标**：把"课件的错"变成"你亲手验证过的知识"，同时直观感受多路召回如何取长补短。
