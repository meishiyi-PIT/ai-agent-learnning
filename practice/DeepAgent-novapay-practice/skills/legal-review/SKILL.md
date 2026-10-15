---
name: legal-review
description: 当需要审查供应商合同、数据处理条款、制裁命中、审计权或责任限制时使用。
---

# Legal Review（法务审查）

## 执行流程

1. 读取 `/policies/vendor-onboarding.md` 的一票否决项。
2. 检查受益所有人、制裁、数据泄露通知、审计权、分包商和数据删除条款。
3. 区分“合同已明确”“合同缺失”“条款冲突”三种状态。
4. 将完整结果写入 `/workspace/findings/legal.md`。

## 返回主 Agent

- 一票否决项是否触发。
- 需要修改的条款及文件位置。
- 外部名单命中及来源。
- 总长度不超过 300 字。

