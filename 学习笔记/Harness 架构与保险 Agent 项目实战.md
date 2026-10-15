# Harness 架构与保险 Agent 项目实战

****

## phaseThree 学习目标与进度（Claude 整理，2026-08-10，当前正在学）

> 理解型。按用户 2026-08-10 定的新规矩：不强制填三问，验收=能口述清单各条 + Q&A 照旧整理。
> 课件：`03-智保通第三阶段：生命周期 Agent 与退款 Worker.md`。主题一句话：从"对话式 Agent"到"可暂停、可恢复、可人工介入的工作流"——LangGraph 编排退保 + 确定性 Worker 执行退款 + MCP 外部资源。

### ✅ 验收清单（能讲清这 6 条就结课）
- [ ] **T-G1 挂载全景**：退保主流程挂在哪（agent 工具 or API+LangGraph 旁路）？agent 新挂了什么工具？Kernel 骨架这次动没动？
- [ ] **T-G2 工作流图**：能画出 申请确认→Planner→Send 并行三检查（金额/原因/期间）→聚合→风险路由→自动通过 / Interrupt 人工→Outbox→Worker→结算终止，并说清每步为什么。
- [ ] **T-G3 中断恢复闭环**：Interrupt / Checkpoint(MySQL) / Command-Resume 三件套怎么配合；为什么恢复≠重跑之前的节点；客户↔运营人格为什么只交接结构化摘要不共享对话。
- [ ] **T-G4 Agent/Worker 边界**：为什么"大模型不直接触碰资金结果"；Worker 不是 Agent（不理解语言、不做决定、只执行已批准任务）；边界表能复述。
- [ ] **T-G5 Worker 可靠性四件套**：Outbox+任务租约 / 幂等键 / 数据库事务 / Redis 单实例租约锁（30s 租约 10s 续约、待命接管）；为什么本地默认单实例；为什么锁不是唯一防线。
- [ ] **T-G6 MCP 解耦**：Client(stdio)/Server 分进程；返回 JSON Schema 结构化结果；不可用时明确降级不编造；为什么用 MCP 而不是普通工具直连。

### 📖 读码路线（delta-first，`git diff phaseTwo origin/phaseThree`）
| 小阶段 | 读什么 | 过关判据 | 对应 |
|---|---|---|---|
| **T0 挂载点** | `agent/tools.py`、`harness/kernel.py` diff | agent 新挂了哪几把工具？退保动作在不在工具里？ | T-G1 |
| **T1 LangGraph 工作流** | `surrender/workflow.py`（主）+ `rules.py`、扫 `service.py` | StateGraph/Send/条件路由怎么写；试算为什么在 rules 不在模型 | T-G2 |
| **T2 中断与恢复** | `surrender/service.py` 审批衔接 + `mysql/langgraph_checkpoint.py`、`api/v1/surrenders.py` | Interrupt 落库了什么；Command 怎么把流程接回去 | T-G3 |
| **T3 退款 Worker** | `commands/run_refund_worker.py` + `refund_worker_runtime.py` + `redis/worker_lock.py` | 轮询/租约/心跳/失锁待命；Outbox→结算事务链 | T-G4/G5 |
| **T4 MCP** | `mcp/partner_resources_server.py` + `infrastructure/mcp/partner_resources.py` | stdio 连接、Schema 校验、超时降级 | T-G6 |

### 🎯 T0 入场预测题
1. 退保是**动资金的重业务**——按 phaseTwo 学到的模式预测：它会做成 agent 工具（模型能调"发起退保"）吗？还是像材料识别一样走 API 旁路？agent 端最多挂什么性质的工具？
2. `kernel.py` 这次动没动？大胆猜。
3. LangGraph 登场了——它和 `create_agent` 的 tool-loop 是**替换**还是**并存**？各管哪类活？

### 📝 读码 Q&A（Claude 追加）

#### T0 挂载点（2026-08-10 已验收）
- phaseThree 新工具只有 3 把且**全部只读**：`list_my_surrenders` / `get_surrender_operations` / `search_partner_institutions`(MCP)。**没有"发起退保"工具**——退保动作走 API 三跳（试算/创建/确认）+ 运营审批，模型碰不到。
- **判定公式（预测题 Q1 答错后立的）：动作有不可逆外部副作用（尤其资金）→ 模型永远只有"查"没有"动"。** 材料识别走旁路（人工闭环）、退保走旁路（动钱），同一条规则两次应用。
- LangGraph 与 create_agent tool-loop **并存**：LangGraph 不在 Kernel 里，挂 `domains/surrender/`，由 API 触发。tool-loop=对话咨询（不碰钱），LangGraph=业务编排（碰钱）。kernel.py 改动 98+/43-（待扫，推测为新卡片组装）。

#### T1 LangGraph 退保工作流（2026-08-11 验收，两道预测题全对）
- **题眼：workflow.py 里 LLM 调用 = 0 次**（自己数出来的）。Planner 是写死的 4 条计划、检查是阈值（≥300元）/关键词表/标志位、路由是 if HIGH——**钱的流程里模型连"提候选"的资格都没有，直接缺席**。模型只在对话侧（`list_my_surrenders` 解释进度）。phaseThree 分层：对话层(LLM tool-loop) → 编排层(LangGraph 纯确定性) → 执行层(Worker 纯确定性)。
- **全是确定性规则为什么还要 LangGraph？** 价值不是"编排模型"，是给流程上**断点和持久化**：interrupt 暂停 / checkpoint 落库 / Command 恢复 / stream 收集节点事件喂时间线。if/else 函数做不到"跑到一半停几天、换个进程接着跑"。**LangGraph = 可持久化状态机框架**，模型编排只是用途之一。
- **interrupt 不是线程阻塞**（workflow.py:417 注释）：暂停=状态存 MySQL 后该 HTTP 请求正常返回"paused"；恢复=几天后**另一个 HTTP 请求**带 Command(resume) 进来。**两次 HTTP 请求之间，流程活在数据库里**。恢复钥匙 `thread_id="surrender:{request_id}"` 焊在申请数据上。
- 三跳设计（试算→创建→确认）+ Idempotency-Key 请求头 + 审批幂等（已审批状态再点→幂等返回现状不报错，service.py:329）。
- 设计取舍：check_reason 关键词表会漏报（"你们乱扣钱"不含敏感词）——规则宁可漏报也要**可审计可复现**，金额阈值兜底，漏报进的是"自动通过+可追溯"。

#### T2 Checkpoint 落库（2026-08-11 快过）
- 三张表：`LangGraphCheckpointRecord`=状态快照+父指针（git commit）/ `LangGraphBlobRecord`=channel 版本化值（git 对象库）/ `LangGraphWriteRecord`=interrupt 时未提交写入（暂存区）。
- 恢复链：审批请求→resume_review→Command→图按 thread_id 调 get_tuple 从 MySQL 装回状态→从 interrupt 点继续。**进程死活无关，流程活在数据库里，进程只是过客**。`compile(checkpointer=...)` 一个参数买到全部能力。
- blobs 带 version 的原因：一个 thread 一串 checkpoint，每个 checkpoint 只记"各 channel 当时的版本号"，没变的 channel 不重复存值、多 checkpoint 共享同一版本 blob——git commit 引用对象同理。

#### T3 退款 Worker（2026-08-15 验收）
- **Q（我问）：Idempotency-Key 请求头怎么做到幂等？** Header 只是传声筒。**幂等三件套** = ①前端生成"意图键"（一次意图一个键，重试不换键）+ ②服务端按(user_id,键)查重、命中**返回原申请（200）而不是报错** + ③DB 唯一约束 `uq_surrender_user_idempotency` 兜并发底（两请求同时过了 SELECT，后到的 INSERT 被拒）。同款三件套遍布全项目：订单/支付/退款尝试/时间线。
- **Lua 验 owner 的真正作用 = "我还不是主"探测器**：A 卡死→锁过期→B 上位→A 缓过来。裸 DEL 会删掉 B 的锁（变三主）；裸 EXPIRE 让 A 续约"成功"继续当主（双主长存）。验 owner 后 renew 返回 0→A 触发 lease_lost 停手。**"检查再操作"分两条命令必有竞态，必须 Lua 原子化**（= Java compareAndSet）。
- **双活窗口防线从外到内**：⓪Redis 租约+心跳（只把双活窗口压到秒级）→ ①DB 任务租约（claim 原子写 worker_id+leased_until，一条事件只被一方领走）→ ②幂等尝试复用（已有 SUBMITTED/成功单→复用不造新 refund_no；refund_no/idempotency_key DB unique）→ ③收敛式结算（settlement 不做"加一笔"只做"设终态"，SUCCEEDED 设两次还是 SUCCEEDED，天然可重放；四项同事务；时间线唯一幂等键）→ ④渠道幂等键（真实渠道边界，本项目 INTERNAL 模拟）。**结论：处理动作可能发生两次，资金结果只会有一个**——"至少一次投递+幂等处理"的完整实装。
- **哲学（脊柱级）**：**每一层都假设外面那层会破**。锁会丢、租约会过期、事件会被重复消费——兜底永远是最内层"幂等+收敛+唯一约束"；**锁不负责正确性，只负责秩序**（控节奏、日志可解释）。与 phaseTwo"闸门下沉、深层不信上层"同一条脊柱。
- 其他：指数退避 `min(2**n, 60)` 防雪崩、5 次转 DEAD 交运营 requeue/cancel（"重试只治偶发治不了必然"实装）；runtime/业务/锁三文件各管一层（"如何持续运行"与"退款业务规则"分离），Protocol 解耦——后台 Worker 类程序的标准骨架，可抄。

### 进度锚点
**当前：T4 MCP**（最后一段）——读 `mcp/partner_resources_server.py`（独立 Server）+ `infrastructure/mcp/partner_resources.py`（Client 适配器）。T0-T3 已完。收官待验收：T-G1~G6 口述。

---

## phaseTwo 学习目标与进度（Claude 整理骨架，2026-08-09，✅ 已完结 2026-08-10）

> 理解型：能讲清「架构 + 主流程 + 指得到是哪个文件哪一步」即算掌握，不要求默写实现、不要求手写。

### ✅ 阶段验收清单（学完能讲清这 6 条就过关）
- [x] **G1 总纲**：新能力 = 注册成受控工具挂到 phaseOne 那个没变的 Kernel；能在代码里指出挂载点（`tools.py` 注册 + `kernel.py` 引用聚合），并说清内核骨架几乎没动。✅ 2026-08-09 S0 验收（含修正：材料识别是旁路不是工具）
- [x] **G2 三类上下文分治**：知识 / 长期记忆 / 业务事实 三者的「来源·可信度·生命周期」不同，不能混成一段无来源上下文。✅ 2026-08-10 收官考验收（关卡对照表见 Q&A S2/S4 段）
- [x] **G3 RAG「有依据」**：检索只给候选证据 → 判断证据是否直接支持结论 → 引用聚合 → 拒绝推测；混合检索每一步（向量 / BM25 / RRF / Rerank / 降级）为什么存在。✅ 2026-08-09 S1 验收
- [x] **G4 记忆「授权+隔离+脱敏」**：明确授权才写、按用户隔离、敏感拦截、MySQL 元数据 + Milvus 向量分工、可召回可删除。✅ 2026-08-10 验收（两处修正：owner_id=登录态从context焊死非"生成"；授权门是软约束、硬约束负责封顶伤害）
- [x] **G5 多模态「不可信输入+网关隔离」**：原图不直接喂模型（预处理）、独立 vision_gateway、固定 Schema、材料文字防注入。✅ 2026-08-10 验收
- [x] **G6 趋势「白名单非自由 SQL」**：模型只选 指标/时间/维度，后端白名单查 Analytics 库。✅ 2026-08-10 验收（修正：SQL 非"写死"而是运行时由代码按白名单编译，模型输入不进 SQL 字符串）

### 📖 读码小阶段路线（每块只读列出的文件，delta-first）
| 小阶段 | 读什么 | 过关判据（能答即过） | 对应 |
|---|---|---|---|
| **S0 挂载点** | `agent/tools.py`、`harness/kernel.py` 的 diff | 新注册了哪几把工具？内核改了哪一处（引用聚合）、其余没动？ | G1 |
| **S1 Agentic RAG** | `knowledge/service.py`+`chunking.py`+`retrieval.py`，扫 `milvus/knowledge_index`、`embedding/bge·reranker` | 画出 query→检索→融合→重排→引用聚合→拒绝推测；说清「上传→索引→测试→发布」为什么可审计 | G3、G2 |
| **S2 长期记忆** | `agent/memory.py`，扫 `milvus/memory_index` | 授权门+敏感检查在哪？怎么按用户隔离？reply 哪一步召回？ | G4、G2 |
| **S3 多模态** | `service_request/preprocessing.py`、`bailian/vision_gateway.py`，扫 `service_request/service.py` | 预处理为什么在模型之前？vision_gateway 为什么独立？怎么防注入？ | G5 |
| **S4 运营趋势** | `mysql/analytics_queries.py`，扫 `tools.py` 趋势工具段 | 白名单查询长什么样？Core→Analytics 怎么同步？为什么不给 SQL？ | G6 |

### ❓ 三问（正文我自己填）
**① 是什么** —— 

**② 为什么** —— 

**③ 怎么做** —— 

### 🎯 各小阶段入场预测题（先答→自读→Claude 校对补「架构 why」）
- **S1**：RAG 命门比 phaseOne「多了哪一层」？为什么知识要走「上传→索引→测试→发布」而不直接写向量？
- **S2**：长期记忆加在哪一层（Turn/Thread/Task/Memory/Audit）、存哪种库、reply 哪一步被召回？
- **S3**：为什么单开 vision_gateway 不复用 model_gateway？材料里的文字防什么攻击？

### 📝 读码 Q&A（学习中问过的，Claude 后续追加）

#### S0 挂载点（2026-08-09）
- **Q：phaseTwo 新挂了哪几把工具？** 5 把（`tools.py:788-843`）：`search_insurance_knowledge`（RAG）、`query_operation_analytics`（趋势）、`remember/recall/forget_customer_memory`（记忆×3）。**修正**：文档说 4 大块，但只有 3 块成了工具——**材料识别没有工具**，走 `domains/service_request/` 旁路管线（自己的上传 API，不进 tool-loop）。为什么不做成工具：①要"客户确认→运营审核"人工闭环，一次 tool-call 走不完；②图片走独立百炼 Qwen-VL 网关，与 DeepSeek 文本物理隔离；③材料 OCR 文字=不可信输入，必须先固定 Schema 抽取落成结构化事实，不能让模型在自由 tool-call 里直接吞。
- **Q：kernel 改了哪？** 骨架 `persona→create_agent→invoke→_structured_output→AgentReply` 一行没动；只加"来源聚合"：滤掉工具自吐的 knowledge_sources 块（`kernel.py:149`），用模型声明的 ZBT_CITATIONS ∩ 本轮真实工具执行记录重建（`_knowledge_sources_block`）。

#### S1 Agentic RAG（2026-08-09）
- **Q（我问）：LLM 返回的 chunk_id 和工具的还会不一样吗？为什么要再匹配一遍？** 会，防的就是不一样。原则=**永远不信模型自称的来源**：模型可能编造 id / 引上一轮旧 id / 挂羊头（答案来自先验却挂 id 装有依据）。前端展示的依据 = **模型声称引用 ∩ 本轮真实检索到**（kernel `if chunk_id in candidates`）——只信模型会展示假来源，全展示又不精确（检索 5 条只用 2 条）。另注意：chunk_id 不是查询时临时切的，是**索引阶段生成的稳定 id** `文档id:版本:段号`（`knowledge/service.py:340`）。
- **Q（我问）：phaseOne 也有 prompt/skill，为什么 phaseTwo 就能答复杂问题？** 质变不在 prompt，在于给了模型**受治理、可检索、带版本、可追溯的外部知识库 + 硬约束**（`answer_constraints`：direct_evidence_only / no_numeric_inference / 答不了回"当前知识库未明确"，`tools.py:559`）。一句话：phaseOne 让模型会用工具办事，phaseTwo 让模型有依据答疑、答不了就承认。
- **Q（我问）："Agentic" 具体落在代码哪里？** 三处：① **硬约束面** `tools.py:487-505`——用 `context.executions` 数本轮同名执行算 attempt，>3 直接 raise `AGENTIC_RETRIEVAL_LIMIT_REACHED`；工具结果里带 `agentic_retrieval.next_step`（refine_query / evaluate_evidence）引导模型下一步。② **多问题改写**：`alternate_queries` 每个改写独立检索，工具层再跨问题 RRF 融合（`_fuse_knowledge_rankings` `tools.py:865`）。③ **软约束面** `skills/insurance-knowledge/SKILL.md`——拆子问题→首轮原问题+≤2 改写→逐项判断证据→不足缩小范围再检索（≤3 轮、不得重复同一问题）→3 轮仍不足必须拒答。循环本体就是 `create_agent` 的 tool-loop，kernel 没为此改任何东西。
- **预测题修正**：①降级分两级——召回是命根（Milvus 挂→硬 raise 503），精排锦上添花（Reranker 挂→try/except 回退 RRF 结果，`knowledge/service.py:306-314`）；②"只查已发布"过滤**不在工具在服务端** `KnowledgeService.search()`（`status=="PUBLISHED"`，注释原话"状态过滤在服务端完成，模型无法绕过"）——和 phaseOne `_resolve_product_plan` 同一套路：**关键闸门往下压**；③候选先放大 4 倍（candidate_multiplier）再融合精排。
- **自己总结时漏的 3 条**：①多轮自主检索（≤3）才配叫 Agentic，不是查一次；②RRF 有两层（服务内 dense+BM25 / 工具层跨改写问题）；③**发布治理门禁**：DRAFT→INDEXED→检索测试→PUBLISHED→可 INACTIVE，且发布必须有"本次索引之后、通过的检索测试"（防"写进库但搜不到"的知识上线，`service.py:124-154`）——保险业务敢用的前提。

#### S2 长期记忆（2026-08-10，另一会话自读 + 本会话收官考修正）
- **修正①：owner_id 不是"创建对话时生成的"**，就是登录态身份：JWT→`H5User`→`ToolExecutionContext`→工具从 `context.h5_user.id` 焊死（`tools.py:646-652`）。模型参数里**没有 owner 字段**——跨用户访问在结构上不可能表达，不是"校验出来的"。phaseOne"身份从 context 拿"的第三次重演。
- **修正②："授权才写"是软约束，不是硬的**。`memory.save()` 硬校验只有：类别白名单 / 长度 2-300 / 敏感正则——**没有一行代码验"用户说过请记住"**（语义事实只在对话里，代码判不了）。授权门靠工具 docstring（"仅在用户明确要求记住时"）+ customer-memory skill。**软硬分工判定标准：代码判得了的全部硬拦；只有对话里才知道的交给 prompt，同时用硬约束把违规最大伤害封顶**（乱调用也写不进敏感号、串不了号、塞不进垃圾）。敏感拦截注释原话："用确定性规则拦截常见敏感号码，不把安全判断交给大模型"（`memory.py:218-226`，手机/身份证/银行卡三条正则）。
- **forget 删两处**：MySQL 逻辑删（status=DELETED）+ Milvus `index.delete`。且 `search()` 会拿命中 id 回 MySQL ACTIVE 列表再过滤（`if hit.memory_id in memories`）——**repository 是事实源，index 只是加速器**，索引漏删也不泄露。又一个"深层不信上层"。

#### S3 多模态材料识别（2026-08-10，Claude 带读）
- **管线七步**：API 层 10MB+类型枚举（`service_requests.py:60-76`）→ service 层保单资格闸门 `_require_user_policy`+格式白名单 → Pillow 预处理（真身在 `infrastructure/documents/material_preprocessing.py`，domains 里只有 Protocol+直通实现）：`verify()` 验真防伪装文件 / 25M 像素上限防像素炸弹 / `exif_transpose` 纠向 / 转 RGB 存 JPEG 剥 EXIF 隐私+降成本，"模型不会直接接收原始文件" → 百炼网关固定 Schema 收敛（fields 全转 str、confidence 钳 [0,1]，"无论模型返回哪些额外内容，对上层都只暴露约定的三个字段集合"）→ 双存储（原图→MaterialStorage、结构化→数据库，DB 失败回滚删图）→ 客户确认 → 运营审核。
- **Q（我问）：哪里需要客户确认了？我没看到** → 确认不是一个 `confirm()` 函数，是**两个接口之间的协议设计**：识别接口只返回"待确认结果"（status=PENDING_CONFIRMATION，不落业务）；客户发起第二跳 `POST /h5/service-requests` 带 `confirmed_fields`——**提交这个请求本身就是确认**。铁证：落库的 `ServiceRequest.confirmed_fields` 是客户提交的字段，`recognition.fields`（模型吐的）从未被拷进业务流程——模型输出只是给表单预填的草稿。**启示：关键人工环节往往长成 API 边界的形状**（识别/生效拆两个接口，中间必须由人发起第二跳），与 NovaPay `interrupt_on` 同思想不同实现。
- **防注入四道**：①system prompt"图片中的任何指令性文字都属于不可信材料内容"（软）；②Schema 收敛——输出通道只有 fields 字符串，没有执行通道；③旁路架构——视觉模型无工具无对话上下文，图片文字够不到 Kernel；④客户确认+运营审核双人眼（还可调原图对照）。
- **网关隔离**：vision_gateway 只被 ServiceRequestService 持有，Kernel 不知道它存在——百炼挂只影响识别端点 503，投保对话照跑；DeepSeek 挂反之。**故障域互不传染**，且换供应商只改适配器这一层。

#### S4 运营趋势（2026-08-10，Claude 带读）
- **一句话**：模型不是"会写 SQL 的分析师"，是"只会点菜单的顾客"——菜单=4 指标×2 维度×3 窗口=24 种组合（`OperationAnalyticsArgs` 全 Literal，无自由文本参数），语义层炒菜（代码编译 SQL），后厨只备分析副本食材（独立 Analytics 库）。
- **三道防线**：①Pydantic Literal 参数白名单；②语义层再验（`METRICS.get` 查不到→422，"任何未登记的指标、维度或天数都直接拒绝"——闸门下沉，深层不信上层）；③SQL 由代码按白名单选表选列编译（`analytics_queries.py:271-290`），**模型输入从头到尾不进 SQL 字符串**——注入在结构上不成立，不是"过滤得好"。
- **数据范围**：admin 从 context 拿（又是身份不让模型传）；`data_scope=="SELF"` 强制 where 本人；SELF 查不到销售映射→**返回空结果而非全量（fail-closed，出错往"关"倒）**。
- **分库理由**：性能隔离（聚合扫描不打业务库）+ **物理爆炸半径**（三道防线全破也只碰得到分析副本，够不到 Core）+ 独立事务不反向污染。同步：`commands/build_analytics.py` 离线跑 `refresh()` 快照成星型模型（dim_date/product/salesperson + fact_orders/policies）。
- **透明度**：返回值带 `query_plan`（fact/aggregation/filters/read_only）供审计；ChartBlock 由工具从真实 rows 生成，不是模型画的。

#### 收官考 G2 关卡对照表（三类上下文"谁说了算"不同，入口关卡分开修）
| 上下文 | 来源 | 入库关卡 | 消费关卡 |
|---|---|---|---|
| 知识 | 运营上传文档 | 索引→检索测试→发布 | 只查 PUBLISHED + 引用∩真实执行 |
| 记忆 | 用户主动授权的偏好 | 敏感正则+类别白名单+owner 焊死 | 按 owner 隔离 + repository 兜底过滤 |
| 业务事实 | 真实交易/用户确认+运营审核 | 业务规则/状态机/双人背书 | 工具查库 + `_safe_*` 脱敏 |

### 进度锚点
**phaseTwo 全部完成（2026-08-10）**：S0-S4 走完，G1-G6 全部验收 ✅。待办：①看视频 `04`（第四步验证补漏）；②phaseThree 读码（`git diff origin/phaseTwo origin/phaseThree`，四块：退保 LangGraph 编排 / 退款 Worker / MCP / 可观测性）。

---

<!-- ↓ 以下为 phaseOne 复习参考 ↓ -->

  - 核心闭环：我理解好像和我看的deepagent项目还有agentic agent的流程是类似的
  - harness 受控任务链-我理解就是langgraph或者在deepagent里学到的动态规划，但是动态规划实际上也算是可控的把，因为决策的权力还是在supervisor里，记录用langsmith，恢复用checkpointer，终止也是一种我觉得langgraph里的任务台吧，审计是什么，是不是也是langsmith



## Harness 是什么

  1. 解决什么问题？
       模型只负责"提出下一步做什么"，但谁来决定这一步能不能执行、状态存哪、失败了怎么恢复、出事了怎么追责？这套运行控制层就是
         Harness。一句话：模型提候选，Harness 管裁决。

  2. 核心模式是哪两个？ ① 核心闭环：感知→规划→行动→观察（第一部分第 4 节）；②
       任务状态机：READY/RUNNING/WAITING_APPROVAL/BLOCKED…（第二部分第 3 节，全文最重要的一张图）。

  3. 对应你已有的哪些代码？ 这是提效关键——这份课件讲的东西你其实全都见过：

         │          课件概念           │                                 你已经见过的实物                                  │
         ├─────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────┤
         │ 人工审批 / WAITING_APPROVAL │ NovaPay 里的 interrupt_on（提交动作要人工确认）                                   │
         ├─────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────┤
         │ 权限策略 allow/ask/deny     │ 课件里那段 yaml 就是 Claude Code 的权限配置格式；NovaPay 用权限 glob              │
         │                             │ 挡政策文件是同一思想                                                              │
         ├─────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────┤
         │ "确定性落在代码不落在       │ NovaPay 三原则之三：Pydantic 枚举挡非法决定                                       │
         │ Prompt"                     │                                                                                   │
         ├─────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────┤
         │ Checkpoint 与恢复           │ LangGraph 的 checkpointer（复习笔记 08）                                          │
         ├─────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────┤
         │ Trace / 可观测性            │ LangSmith（VendorGuard 评估实战）                                                 │
         ├─────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────┤
         │ Harness 实物样本            │ 你现在正在用的 Claude Code 本身——04 课件源码解读讲的就是它        

  读完回来答我 3 道题（费曼检验，答不上的才需要回头补）：
    1. 用一句话说清：模型和 Harness 各自负责什么？
         1. 模型负责解决问题，harness负责流程上的事情，我理解是让大模型的输入更准确，以及使用的用户体验感更好。
    2. NovaPay 的 interrupt_on 对应状态机里的哪条转移路径？被拒绝后任务进入什么状态？
         1. 我觉得对了权限和策略把，被拒绝之后的会拒绝续约，然后结束任务？
    3. 为什么说"模型上下文只是临时视图，任务状态才是权威来源"？反过来会出什么事？
         1. 因为我理解任务的状态才是判断这个流程是否进行流转的实际的判断来源。反过来的话应该就是把决策权交给大模型了。

## 为什么要用 Harness

## Harness 怎么用



---

## 学习中问过的问题（Claude 整理，2026-08-08）

### Q1：Harness 对比 deepagents 的变化在哪？感觉它早就有 trace/记忆/checkpointer 了
没有新组件——**deepagents 就是 Harness 的一个实现**。模块四的变化是视角：从"使用现成框架"换成"自己搭建"（智保通项目要用 FastAPI 亲手搭这些层）。零件对照：todo list=任务建模/状态；subagent+filesystem=执行隔离；interrupt_on=审批；LangSmith=Trace；checkpointer=恢复。

### Q2：任务状态那个 JSON 没看明白
把它当成**给 Agent 开的 JIRA 工单**：goal=标题、constraints=验收要求、current_step=当前环节、completed_steps=已完成、pending_questions=阻塞项（在等谁）、artifacts=附件、status=工单状态。为什么必须有它：消息历史=群聊记录，任务状态=工单——查进度看工单，不翻聊天记录。prompt 是每轮可重新渲染的"页面"，状态才是"数据库"，崩溃/压缩后靠它恢复（checkpointer 只是存取机制，存的内容就是它）。

### Q3：三类流向里到底有什么、什么必须传？为什么 State 要设计那些字段？
按"**谁消费这条信息**"归位：
- 数据流 = 任务内容（输入、检索结果、产物）→ 给下一步的模型/工具用，类比方法参数和返回值
- 控制流 = 下一步走哪（current_step、路由决定、重试计数）→ 给**编排器**用，类比 if/else 和状态机
- 执行流 = 动作在哪以什么权限跑（工具调用、超时、沙箱）→ 给运行时用，类比线程池/事务管理器

Agentic RAG 对号：messages/检索结果=数据流；路由函数返回 "rewrite"=控制流（条件边是载体）；ToolNode 调 Tavily=执行流。
**State 字段取舍标准一句话：这个字段丢了，任务还能正确走下去吗？** 能→不放，不能→必须放（大结果放文件，State 只存索引）。

### Q4：失败重试那段描述没看懂
它就是 Java 的 **catch 不同异常做不同处理**：临时网络错误/限流→退避重试（@Retryable+backoff）；信息缺失→**不是错误**，转 WAITING_INPUT 等补充；计划/语义错误→**重试没用**（同样输入再跑还是错），要改输入或重新规划；权限拒绝→走审批，不重试。总纲：**重试只治"偶发"，治不了"必然"**；这张表就是状态机图的文字版。
幂等键 = 接口防重的 requestId。写操作超时 = **结果未知 ≠ 失败**：先查证 → 有幂等键才允许重放 → 没有就转人工/补偿，副作用记台账（"已发起、结果未知"）。"至少一次 + 幂等处理" = MQ 消费者语义。

### Q5（你笔记开头自留的疑问）：审计是什么？是不是也是 LangSmith？
不完全是。**可观测性回答"系统怎么跑的"，审计回答"能否证明关键动作合规"**。两者可以共享 trace_id，但审计记录要求更严格：独立访问控制、保留周期、完整性保护、不可抵赖——LangSmith 是可观测性工具；审计一般是单独的、只追加不可改的记录（权限判定、审批结果、数据访问）。出处：课件第三部分第 5 节末段。

### 检验题修正记录（聊天里快问快答那三题）
- "控制流不能靠模型"的理由：幻觉只是表现之一，根本原因是 prompt 里的决定**不可强制、不可审计、不可恢复**——即使模型不犯错，也无法证明任务走了合法路径。
- "重试会触发幂等"有隐藏前提：**幂等是设计出来的，不是自动存在的**。工具没设计幂等键时，重试可能把退款做两次。

### Q6（第二部分）：结构化计划记不住
不用背，会推导即可。计划只回答三问：每步**谁干**（type/tool）、**什么顺序**（depends_on）、**危不危险**（risk→要不要审批），加上 inputs/outputs 让数据流可追。类比 Jenkins pipeline：不背字段，知道必须声明 stage/依赖/超时。自测：合上课件给"生成周报"设计一个计划 JSON，覆盖这四类信息就算会。

### Q7（第二部分）：状态机文字没看懂（图看懂了）
文字 = 三句话：①图里的边是唯一合法走法，没画的转移编排器直接拒绝（订单不能从"待支付"跳"已收货"）；②模型只能**申请**转移，不能改规则；③每个步骤随身五件装备：trace_id、cancellation_token、超时、重试上限、幂等键。并行条件 = 无写入冲突、无顺序依赖（同多线程共享变量道理）。

### Q8（第二部分）：沙箱到底怎么实现
沙箱不是一个组件，是"关笼子"手段的总称，核心思想：**不信任要执行的动作，给它一个使坏也出不了圈的环境**。按强度四级：①代码级校验（路径 resolve 后限定目录、SQL 只放 SELECT——NovaPay 权限 glob、deepagents filesystem 就是）；②进程级（子进程+超时+低权限；参数数组执行命令 = Java 里 PreparedStatement 防注入的思想）；③容器级（Docker：挂载目录=文件边界、白名单=网络边界、配额=资源边界）；④虚拟机级（最强）。实物：Claude Code 跑命令时的权限确认框=策略引擎，受限执行=沙箱。

### Q9（第二部分）：工具 JSON / 权限 YAML 没看懂 + 和文字对不上
**对不上是课件示例不完整**：文字列六要素（schema/结构化输出/超时/风险等级/副作用声明/审计标识），示例只展示三个（input_schema、timeout_ms、readonly），风险等级和审计标识缺失——查漏正确，可记勘误。
工具 JSON：input_schema=参数说明书（query 必填 string，max_rows 默认 1000），Java 对照 DTO+@Valid；LangChain @tool 背后生成的就是这段。
权限 YAML：就是 Claude Code settings.json 格式。deny→ask→allow→default deny 顺序匹配（先黑名单→审批名单→白名单→默认拒绝），高层禁令不可被低层覆盖；deny 里的 169.254.169.254 是云服务器元数据地址（可偷凭据），写死禁止。

### Q9.5（第二部分）：还是没懂沙箱——"不影响真实数据"的话，更新数据的需求怎么办？
误区来源：把 Harness 的沙箱当成了**支付宝那种"沙箱环境"**（假数据测试环境）。同词不同义。
正确心智模型：**沙箱 = 围栏，管"能碰到什么"，不管"数据真假"**。围栏内的写入是真实的（agent 在 workspace 里写文件是真写）；围栏外的东西物理够不着（没有数据库凭据、网络白名单里没有数据库地址）。
**更新真实数据不翻围栏，走"门"**：受控工具接口（如 refund(order_id, 幂等键)）→ 策略判定 allow/ask/deny → 高风险人工审批（interrupt_on）→ 真正执行 UPDATE → 记审计。沙箱封掉"除了这扇门以外的一切路径"。
类比：银行柜员坐在柜台里（沙箱），柜台内电脑单据随便用（workspace 可写），金库的钱摸不到；转账必须走核心系统接口（工具），大额要主管授权（审批）。隔离不是"不能动钱"，是"动钱只能走接口、留痕、有授权"。
实物：Claude Code 能直接写我 workspace 的文件（围栏内真实写入），跑命令要过权限（门），但它根本没有我公司数据库的密码（凭据不注入 = 最硬的边界）。课件"凭据按需注入、短期有效、用后回收"即此意。

### Q10（第三部分）：状态分层要背吗？
不背表格，记一个判断题：**这条信息要活多久、谁在乎它？** Turn=一轮（循环局部变量）→ Thread=一次会话（LangGraph checkpointer 存的图状态/messages）→ Task=一个任务周期（NovaPay 审批/工单记录、todo list）→ Memory=长期（记忆系统课的向量库/关系库）→ Audit=合规期最长（审计日志）。用法：写代码纠结"这个变量存哪"时，先答活多久，存储位置自动出来。这就是智保通项目数据库表设计的依据。

### Q11（第三部分）：上下文与记忆的最小接口记不住
清单只回答一个问题：**这一轮 prompt 里放什么？** 六项 = 五个自然问题：你是谁能干什么（系统规则权限）、要干什么（目标约束）、干到哪了（计划）、刚才发生了什么（最近交互+工具摘要）、有什么背景可用（相关记忆/Skill）。类比交接班：夜班交白班只说这五件事，不放整周监控录像。这清单就是"上下文工程"的落地——deepagents 每轮拼 prompt 干的就是这个。

### Q12（第三部分）：Checkpoint 为什么覆盖那些时机？
规律一句话：**贵的事、不可逆的事发生之后立刻存；危险的事发生之前先存**（游戏存档：打 boss 前存，拿到装备后存）。逐条：用户输入后=新信息丢了要重问；工具调用前=崩溃后要知道"当时正要调"（否则分不清调没调，对应写操作"结果未知"）；调用后=结果落袋不重调；文件写入后=副作用已发生；审批后=审批必须持久化、恢复后不得重问或绕过；压缩前=要丢信息先留底；交付前=定稿。

### Q13（第三部分）：LangSmith 的 trace 怎么看？
一次 run = 一棵树：root=整个任务，子节点（span）=每次模型调用/工具调用/子代理。看树=看执行回放。五个问题的看法：执行路径=从上往下读树；哪步失败=红色 span；哪里慢=按耗时找最大 span；模型看到/说了什么=点 LLM span 的 Input（完整 prompt）/Output；花多少=token 与成本统计。
**关键联动：LLM span 的 Input 就是 Q11"最小接口"六项清单的实物**——亲眼看一次每轮重新组装的上下文长什么样。

### 沙箱检验题批改（投保单写库）
我的答案："写入发生在沙箱内，调用内部封装好的方法，policy 约束谁能写、什么时候写。"
批改：工具=封装好的窄接口 ✓、policy 裁决 ✓（完整五要素：主体/动作/资源/环境/任务依据）；**但"写入发生在沙箱内"错了**——agent 在沙箱内只是**发起请求**，真正的 UPDATE 由工具代码在沙箱**外**（有凭据、有网络通路的服务里）执行。一句话：**沙箱里发生的是"请求"，围栏外发生的是"执行"**。如果写入真在沙箱内发生，说明沙箱里有数据库凭据和网络通路，围栏就形同虚设。柜员类比：柜员在柜台里按下转账按钮，钱的移动发生在核心系统里。

### Q14：checkpoint 不就是个断点吗？为什么用处那么多？
**混淆了两个词：断点（breakpoint）是"停在哪"，checkpoint 是"存档——记住了什么"。** 断点是调试概念，不保存任何东西，进程还活着；checkpoint 是持久化的**状态快照**，进程死了它还在（LangGraph 的 SqliteSaver 就是数据库里一张 checkpoints 表，每行一个完整 State 快照）。更好的类比是 git commit：不是暂停点，是随时能回去的快照。
用处多的原因：**它是唯一能穿越"进程死亡"的东西**，所有跨进程生命周期的能力都只能建在它上面——
① 崩溃恢复：从最近存档继续，不从头跑；
② **等待/审批的载体**：interrupt_on 触发时 = 存 checkpoint → 进程可退出（不占资源）→ 几天后人批准 → 从存档恢复现场继续。所以 LangGraph 里用 interrupt() 必须先配 checkpointer，否则直接报错；
③ 多轮会话：thread_id + checkpointer = 关掉重开对话还在；
④ 防重复副作用：存档记着"工具调过了、结果是 X"，恢复后不重调；
⑤ 时间旅行调试：从历史快照分叉重跑。


---

## phaseOne 读码时问过的问题（Claude 整理，2026-08-09）

> 上面 Q1–Q14 是 Harness **理论课**的问题；这一节是 phaseOne **读代码**时问的，按读码四块归档。

### Block A · 内核主流程（main.py / kernel.py）

**A1：create_app 分几层？为什么统一在这里装配？**
三层：repository（数据）→ service（业务）→ router（接口），外加 harness 内核。统一装配 = **组合根（composition root）**：所有 new 对象、所有"谁依赖谁"只在这一处接线，别处只管用不管造。好处 = 依赖关系一眼看全、换实现只改一处（测试可喂假 repo）。对照 Java：等于手写的 Spring 容器，只是没有注解自动扫描，靠 create_app 手动 new + 传参。

**A2：AgentKernel 在哪创建、喂了什么？三个 service 要背吗？**
main.py 145–153 创建，喂进 settings、model_gateway、`build_agent_tool_registry(catalog, enrollment, attribution)`。**不用背具体 service**——只需记"内核要拿到能干活的工具，而工具是从 service 包出来的"，哪个 service 用到时再查。

**A3：为什么要 3 个数据库？**
按"数据归谁管"切：core（身份/产品/订单等核心业务）、agent（会话/消息/Run 等 Agent 运行数据）、analytics（运营分析只读）。好处 = 边界清晰、可独立扩容/授权（运营只读 analytics、碰不到 core）。代码里是 `DatabaseName` 枚举 CORE/AGENT/ANALYTICS（sessions.py 15）。

**A4：为什么 admin 和 h5 用不同模型？**
❌ **前提就错了**——model_gateway.py 34 行 `del persona`：persona 被丢弃，两个人格**用同一个模型**。persona 参数留着只是给"将来想给不同人格配不同模型"占位，当前没用。（"查漏"抓到的错觉）

**A5：role / permission 怎么理解？为什么只有 AdminRole 没有 UserRole？**
role = 岗位（一组权限的打包），permission = 单条能力（如 `order:read`）。admin 是内部运营，有 roles/permissions/data_scope（models.py 15–24）；h5 是外部投保用户，只有 id/手机号/状态（models.py 5–12），**天生没有"权限"概念**——他只能操作自己的数据，不需要角色系统。所以没有 UserRole。

**A6：identity / catalog / agent / attribution 四个 repository 各干嘛？**
identity = 用户身份；catalog = 产品目录；agent = 会话/消息/Run；attribution = 获客归因。repository 只做"存取"、不含业务规则（规则在 service）。

### Block A · reply 主流程

**A7：reply 方法主要干什么？**
❌ 我第一次答"创建两个人格 agent、不同流程、决定 skill/tool/policy"——纠正：**一次 reply 只服务一个人格**；两个人格**走同一套流程**（同一个 reply）；persona 决定的是 **Prompt + Skills + 工具白名单**，**不含 policy**（policy 是全局单例、独立于人格）。流程：97 查人格 → 98 拼 system_prompt → 102 建本次 context → 107 挑工具 → 115 `create_agent` 现装 agent → 141 `agent.invoke` → 151 从 context.executions 取受控工具的真实结果拼卡片。

**A8：卡片为什么从工具结果里谨慎解析，不让大模型直接返回？**
因为**大模型有幻觉**，不能保证它把数据库里的产品/金额/订单**原样完整**吐回来。真实业务事实（卡片内容）由 Harness 从"受控工具的真实返回"里解析（context.executions），模型只负责组织话术。这就是"命门"。

**A9：customer / operation agent 什么时候"注册"？是不是每次 reply 重新注册？**
分清两个词：**注册 = 启动装配一次**（PersonaRegistry 把两份人格蓝图、所有 prompt/skill/tool 塞进各自 registry，registries.py 141）；**创建 agent = 每次 reply 一次**（kernel.py 115 `create_agent`，名字 `zhibaotong-{persona.id}`，用完即弃）。你"每次重弄"的直觉，对的是**创建**、不是注册。agent 为什么不能缓存复用：它的工具里焊了**本次请求的身份**（context），复用会串用户/越权。

### Block B · 工具层 = 命门

**B1：service 链路怎么和 reply 串起来？我没看到 reply 的引用。**
看不到是因为 **依赖注入 + Protocol 接口**：service 里写的是 `self._runtime.reply(...)`（service.py 411），`self._runtime` 的类型是 `AgentRuntime` 这个 **Protocol（端口）**、不是 AgentKernel 本身；真正的 AgentKernel 在 main.py 装配时**注入**进去。所以调用点只认接口、看不到具体类——这正是解耦。可替换成 `UnavailableAgentRuntime`（没配 agent 时报 AGENT_NOT_CONFIGURED）。

**B2：reply 到底什么时候被调用？**
外壳 `AgentThreadService` 处理完（校验归属 → 限流 → 存用户消息）后，在 `_invoke`（service.py 411）调 `self._runtime.reply(AgentInvocation(...))`。即：**HTTP 进来 → 外壳净化 → 才轮到内核 reply**。

**B3：工具怎么把 service"焊"进去？**
`build_agent_tool_registry(catalog, enrollment, attribution)` 里用**闭包**：每个工具的 handler 是嵌套函数，记住了外层传进来的 service。例如 `calculate_quote` 132 行 `enrollment.create_quote(...)`——**保费是 service 算的，不是模型算的**。模型只拿到工具 name+description，参数由 Pydantic 校验，policy 查两道（can_use 建时过滤 + authorize 调时强制，纵深防御）。

### Block C · 会话外壳（AgentThreadService）

**C1：记忆存在哪？怎么取？**
模型**无状态**，历史存数据库（agent 库）。每次前端请求带 `threadid`，外壳按它 `list_messages(thread.id)[-12:]` 取最近历史（service.py 319–325）再喂模型。**threadid = 取件码（钥匙），记忆 = 仓库里的货**；钥匙丢了货还在。

**C2：关掉页面再打开，threadid 就没了吗？**
phaseOne 前端保留的 threadid 若是会话级，关页面确实可能丢；而且 phaseOne 客户接口里**没有"列出我的历史会话"端点**（agent.py 只有运营侧 list_threads）。"换设备/清缓存后找回旧会话"要靠**长期记忆**——那是**二/三阶段**才补的能力。（真实架构缺口，不是看漏）

**C3：净化（校验/限流）什么时候、由谁做？**
在真正调 reply **之前**，由外壳 `AgentThreadService` 做：归属校验（`_owned_thread`）→ 限流（`allow_request`）→ 存用户消息 → 才调内核。内核只管"想 + 调工具"，脏活外壳全挡了。

### Block D · 对外接口 + 人格素材

**D1：prompt 和 skill 什么关系？**
prompt（customer.md/operation.md）= 人格的**岗位说明书**（system prompt）；skill（SKILL.md）= 分模块的**操作手册**，frontmatter 声明关联哪些工具、正文写操作规范。`_compose_prompt`（kernel.py 173–185）把 prompt 正文 + 各 skill 的 name/正文**拼成整段 system_prompt**。

**D2：软约束 vs 硬约束（这条最值钱）**
prompt/skill 文字 = **软约束**（好言相劝模型别乱来，如 customer.md"只能来自工具、绝不编造"）；registry 白名单 + policy + Pydantic = **硬约束**（模型犯浑也拍得掉）。两道防线 = Harness 纵深。⚠️ 查漏：skill frontmatter 里的 `tools:` 字段 `_compose_prompt` **没拿它做权限控制**，真正的硬白名单是 `persona.tool_names`，别被误导。

