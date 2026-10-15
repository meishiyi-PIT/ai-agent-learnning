# Reports（报告输出目录）

主 Agent 会将报告写入：

```text
/reports/{供应商}/onboarding-report.md
```

报告由 Agent 在人工审批前生成。人工选择同意或拒绝后，CLI 会在报告末尾追加
“人工审批记录”，包含建议决定、人工处理结果、带时区的处理时间、本机操作账户、
工作流线程、LangSmith Trace 和提交状态。该记录由 CLI 生成，Agent 不得预先填写。

生成的供应商报告默认被 `.gitignore` 忽略。
