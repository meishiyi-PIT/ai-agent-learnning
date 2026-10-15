---
id: renewal-planning
name: 续保规划
personas: customer
tools: get_policy_context, get_renewal_options, search_insurance_knowledge, submit_renewal_advice
---

# 续保规划

客户就自己的保单提出续保、保障升级或方案比较问题时，按以下流程处理：

1. 先调用 `get_policy_context` 确认保单是当前登录用户本人、处于保障中的保单。工具返回保单不可用时，直接说明该保单不可用于续保规划，不得猜测或区分原因，不得透露其他任何保单是否存在。
2. 再调用 `get_renewal_options` 获取候选方案。方案名称和价格只能以工具返回为准，不得自行编造、换算或调整；预算不预设，只以用户在问题中主动说明的为准。
3. 问题涉及等待期、保障责任、报销范围、免责范围等条款事实时，必须调用 `search_insurance_knowledge` 检索已发布知识，并遵守“保险知识检索”技能的证据边界：引用只能来自本次运行实际检索返回的切片，知识库未明确的内容不得凭常识补齐。证据不足时可改写问题继续检索，最多 3 轮；3 轮后仍无依据的部分不再检索。
4. 完成判断后必须调用 `submit_renewal_advice` 提交结构化建议，不得只用自然语言回复代替提交。

决策只能是以下四种之一，前两种必须从两个候选方案中选择：

- `RENEW_ORIGINAL`：维持原方案续保；
- `UPGRADE`：升级保障方案；
- `NEED_MORE_INFORMATION`：用户自身情况没说清楚（预算、关注点等），在 missing_information 中列出需要用户补充的内容；
- `CANNOT_DETERMINE`：知识库没有依据支撑结论，在 missing_information 中说明缺失的知识。

NEED_MORE_INFORMATION 和 CANNOT_DETERMINE 是两种不同状态：前者缺的是用户信息，后者缺的是知识依据，不得混用。事实性结论必须有本次检索的直接证据；无法确定时不得编造理由或生成虚假引用。

业务边界：本技能只输出建议，不得创建续保订单、执行支付或修改原保单状态；客户需要实际办理续保时，引导前往“我的保障”。
