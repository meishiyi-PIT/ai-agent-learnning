"""续保规划：业务背景与全链路地图。

=============================================================================
一、这个功能在业务上解决什么问题
=============================================================================

用户手里有一张快到期的保单（安心医疗险），他想问一句话：
"我这张保单，是照原样续，还是升级？"

这个问题**没法用纯代码算出答案**，因为答案取决于三类信息：

  1. 硬信息（数据库里有）：这张保单是谁的、还在不在保、什么产品什么计划
  2. 规则信息（知识库里有）：等待期怎么算、升级后保障责任差在哪、报销范围
  3. 软信息（只有对话里才有）：用户的预算、他在意什么

只有第 1 类能用 if/else 判。第 2、3 类要"读条款 + 理解用户意图"，这正是
大模型擅长的。所以设计成一个 Agent：给它三把只读工具（查保单 / 列方案 /
查条款），让它自己判断，最后**必须**调第四把工具把结论交回来。

关键设计问题：为什么结论必须走工具提交，不能让模型用自然语言说？

  因为自然语言没法校验。模型可以随口说"建议升级，年费 8888 元"——这个数字
  是它编的，代码拦不住。走工具就不一样了：参数进了 submit_renewal_advice，
  代码就能当场卡死——方案代号必须是我给的两个之一、引用的知识切片必须是
  它这一轮真的检索到过的。

这就是本项目反复出现的"软硬分工"：
  **判断交给模型（软），但凡代码判得了的一律代码判死（硬）。**
  模型只负责"选哪个"，不负责"有哪些可选"和"数字是多少"。

=============================================================================
二、四种决策的区别（业务核心，写代码前必须分清）
=============================================================================

  RENEW_ORIGINAL        维持原方案续保      ─┐ 这两种是"给得出结论"，
  UPGRADE               升级保障方案        ─┘ 必须从两个候选方案里选一个

  NEED_MORE_INFORMATION 缺的是**用户信息**（预算、关注点没说清）
  CANNOT_DETERMINE      缺的是**知识依据**（知识库里查不到支撑）

后两种最容易混。判断标准很简单：
  再问用户一句就能解决 → NEED_MORE_INFORMATION
  用户说什么都没用、知识库里根本没这条 → CANNOT_DETERMINE

这两种情况下 missing_information 都不能为空——不能只说"无法确定"就完了，
必须说清楚缺什么。业务规则全文见 harness/assets/skills/renewal-planning/SKILL.md，
那份 SKILL.md 就是这个功能的需求文档。

=============================================================================
三、一次请求的全链路（改代码时按这张图定位）
=============================================================================

  HTTP POST /h5/agent/renewal-advice  {policy_id, question}
      │
      ▼
  ①  api/v1/renewal_advice.py          路由层
      │   · 从 Bearer Token 认出用户（身份只能从这里来，绝不让模型传）
      │   · 校验请求参数
      ▼
  ②  domains/renewal/service.py        编排层（RenewalAdviceService）
      │   · 预校验保单：属于本人且保障中，不过就 404，不启动 Agent
      │   · create_customer_thread() 建会话
      │   · send_customer_message()  把"保单ID + 用户问题"发给 Agent
      │   · 【等 Agent 跑完】从返回结果里捞出结构化卡片，拼成 HTTP 响应
      ▼
  ③  harness/kernel.py                 Agent Kernel（现成的，不用改）
      │   · 装载 renewal-planning 技能，按 SKILL.md 的流程调工具
      ▼
  ④  domains/agent/tools.py            工具层（作业含金量最高的一层）
      │   get_policy_context      查保单 + 统一错误 + 字段裁剪
      │   get_renewal_options     列出两个候选方案（唯一真相来源）
      │   search_insurance_knowledge  查条款（现成的，直接复用）
      │   submit_renewal_advice   ★七条校验闸门，全作业的核心
      ▼
  ⑤  harness/schemas.py                协议层
          RenewalAdviceBlock      结构化结论的形状定义

=============================================================================
四、最关键的一条数据通路：Agent 的结论怎么变成 HTTP 响应
=============================================================================

这条链断在哪里，第 ② 站就拿不到结果。四个环节缺一不可：

  1. tools.py    submit_renewal_advice 返回
                 HarnessToolResult(summary=..., blocks=[RenewalAdviceBlock(...)])
                                                ^^^^^^ 必须是 blocks，不是 data
  2. kernel.py:166  cards = [block.model_dump(mode="json") for block in blocks]
                    → cards 只从 blocks 来，放进 data 的东西永远到不了这里
  3. agent/service.py:502  send_customer_message 的返回 dict：
                    {"run_id", "thread_id", "status", "assistant_message",
                     "trace_id", "trace_url", "invoked_tools"}
                    其中 assistant_message["cards"] 就是上一步的 cards
  4. renewal/service.py    从 cards 里找 type == "renewal_advice" 的那一张，
                           它的字段就是响应里 recommendation / missing_information /
                           evidence 的全部来源

记住 data 和 blocks 的分工：
  data=   给**模型**看的原始数据（下一轮推理的输入）
  blocks= 给**前端和服务层**看的结构化卡片（会变成 cards）
现成样板见 tools.py 的 search_insurance_knowledge（约 :735-760），
它同时用了 data= 和 blocks=，对照着看一眼就懂。

=============================================================================
五、本仓库的类型约定（记住这条能消掉大半的类型错误）
=============================================================================

  domains/*/service.py 各服务之间传 **dict**
      enrollment.list_policies(user)  →  {"items": [ {...}, {...} ], "total": n}
      thread_service.send_customer_message(...)  →  dict
      取值用方括号：policy["policy_id"]，不是 policy.policy_id

  harness/ 内部传 **Pydantic 模型 / dataclass**
      HarnessToolResult、RenewalAdviceBlock、ToolExecutionContext
      取值用点号：execution.name、result.data

判断方法：看函数签名的返回类型注解。写着 -> dict[str, Any] 就用方括号，
写着 -> HarnessToolResult 就用点号。
"""
