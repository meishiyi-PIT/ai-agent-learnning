---
name: finance-review
description: 当需要分析供应商偿付能力、现金流、收入集中度、履约表现或供应中断风险时使用。
---

# Finance Review（财务审查）

## 执行流程

1. 读取供应商财务 CSV 与主数据工具结果。
2. 计算 Current Ratio（流动比率）和 Debt Ratio（资产负债率）。
3. 检查收入下滑、现金流转负、交付延误和争议记录。
4. 缺少字段时记录 Unknown，不得补造数字。
5. 将完整结果写入 `/workspace/findings/finance.md`。

## 参考阈值

- 流动比率低于 1.0：至少 medium。
- 资产负债率高于 80%：至少 high。
- 经营现金流连续两年为负：至少 high。

## 返回主 Agent

只返回关键指标、异常项、风险等级和置信度，最多 300 字。

