# NovaPay 作业重做指南（自己填代码版）

> 本项目是从 `C:\workspace\DeepAgent`（ACME 准入基线）复制出来的干净起点，
> 依赖已装好（`uv sync` 完成），基线 46 个测试全部通过。
> 参考答案在 `C:\workspace\meishiyi\08_DeepAgent`——**先自己写，卡住再对照**。
> 对应课件：`AI大模型应用开发\模块三…\课件\8.DeepAgents 项目实战\3.LangSmith 基础与 VendorGuard 可观测评估实战.md` 第十五、十六节。

## 作业本质（一句话）

在"ACME 准入尽调"这条既有工作流**旁边**，平行加一条"NOVAPAY 续约复审"工作流
（新材料 + 新政策 + 新决定类型 + 新提交工具 + 新主管协议 + CLI 开关 + 数据集新样例），
**默认行为一行不变**，然后用 LangSmith 的"基线实验 vs 修改后实验"证明：
老功能没改坏（ACME 分数不降）、新功能达标（NOVAPAY 样例通过四个评估器）。

## 三条总原则

1. **改动顺序 = 依赖顺序**：数据（无代码）→ 纯 Python 层（schemas→tools）→
   装配层（agent→cli→observability）→ 评估层（dataset→evaluation）。
   每步做完跑一次测试再进下一步，别一口气全改完再调。
2. **平行扩展，不覆盖**：所有新参数都带默认值 `"onboarding"`，
   保证 `uv run vendor-guard ACME` 的行为和扩展前逐字节一致——这是两次实验可比的前提。
3. **确定性落在代码，不落在 Prompt**：合法决定集合靠 Pydantic 枚举挡、
   政策文件靠权限 glob 挡、提交动作靠 interrupt_on 挡。Prompt 只做行为引导。

---

## Step 0：先跑基线实验（动任何代码之前！）

作业 15.4 第 1 条要求"修改代码前"跑基线——顺序错了实验就不可比，无法补救。

```bash
# .env 里确认：DEEPSEEK_API_KEY、LANGSMITH_API_KEY、
#             LANGSMITH_TRACING=true、LANGSMITH_PROJECT=vendor-guard-course
uv run vendor-guard-create-dataset --dataset vendor-guard-onboarding-v1
uv run vendor-guard-evaluate --dataset vendor-guard-onboarding-v1 --experiment-prefix vendor-guard-baseline
```

- [ ] LangSmith 上能看到 3 条 ACME 样例、四个评估器都有分数
- [ ] 截图（这是最终要交的证据之一）

## Step 1：NOVAPAY 原始材料（纯写文档，不写代码）

建 `data-room/NOVAPAY/`，五个文件（对照 ACME 目录的同名文件找格式感觉）：

| 文件 | 要埋进去的线索 |
|---|---|
| `security-questionnaire.md` | 自述"无未整改高危漏洞"（**故意与渗透报告冲突**） |
| `pentest-report.md` | 一项未关闭的高危越权访问问题（带编号、日期） |
| `contract-draft.md` | 允许境外分包，但**缺**数据处理责任/通知时限/退出删除证明条款 |
| `financials.csv` | 收入同比 -25%、现金跑道约 8 个月（数字要能算出来） |
| `delivery-performance.md` | 两次工资文件延迟交付记录（日期与财务恶化期呼应） |

课件红线：**线索必须分散**在不同文件、至少 1 处冲突 + 1 处关键缺失
（撞库事件"无独立调查报告"就是那处缺失，放到 Step 2 的 fixtures 里），
不得把结论写在一个文件里让 Agent 照抄。

- [ ] 自检：只看这五个文件 + fixtures，人肉能推出课件 15.2 的全部 5 条线索吗？
- [ ] 日期、金额、事件在文件之间能互相核对（比如渗透报告日期晚于问卷日期）

## Step 2：fixtures + 材料一致性测试

给三个 JSON 加 NOVAPAY 条目（**sanctions.json 不加**——课件要求"制裁查询不命中"，
不命中 = 查无此人，正好测"空结果"路径）：

- `vendor_registry.json`：主数据 + 付款/履约（两次延迟交付要有记录）
- `security_incidents.json`：半年前撞库事件，字段里体现"供应商自称无泄露、无独立调查报告"
- `adverse_news.json`：裁员 + 融资失败报道

然后新建 `tests/test_novapay_materials.py`（参考答案叫 `test_renewal_workflow.py`
里的 `NovapayMaterialConsistencyTests`），用 unittest 断言：

- 问卷文本与渗透报告确实矛盾（两个文件各含关键句）
- 撞库记录标注了"缺独立调查"
- 合同草案列出了缺失条款
- financials.csv 能解析出收入下降与现金跑道

这些测试**不调模型**，就是读文件 + 字符串/数字断言——这正是课件"能规则化的用纯代码测"的落点。

- [ ] `uv run python -m unittest discover -s tests` 全绿

## Step 3：`policies/vendor-renewal.md`

写三档判定规则（renew / conditional-renew / no-renew），每档给可核对的条件，例如：
"存在未整改高危漏洞 → 最高只能 conditional-renew"、"现金跑道 < 合同期 → 不得直接 renew"。

关键认知：`backends.py` 里 `/policies/` 的写保护是 **glob 匹配整个目录**，
新文件放进去自动被保护，**不需要改 backends.py**。
写个小测试证明这一点（参考 `RenewalPolicyProtectionTests`）：断言权限规则里
`/policies/` 的 deny-write glob 能匹配 `vendor-renewal.md`。

## Step 4：`schemas.py` —— 续约决定的类型

加两个东西：

1. `RenewalDecisionType(StrEnum)`：`RENEW = "renew"`、`CONDITIONAL_RENEW = "conditional-renew"`、`NO_RENEW = "no-renew"`
2. `RenewalDecision(BaseModel)`：`vendor_name: str`、`decision: RenewalDecisionType`、`report_path: str`

设计思考（面试级问题，值得自己想清楚再看答案）：
- 为什么不复用 `OnboardingDecision`？→ 两个流程的合法决定集合不同，混用就得靠注释约定。
- 为什么 decision 用枚举而老模型用裸 str？→ 拼错的值在模型边界立刻被 Pydantic 打回，
  而不是流到采购系统。这是对老代码的**改进**，不只是模仿。

## Step 5：`tools.py` —— 续约提交工具

新建 `@tool def submit_renewal_decision(vendor_name, decision, report_path) -> str`，
函数体里**先过 `RenewalDecision(...)` 校验再返回确认文案**——非法 decision 抛
ValidationError，会作为工具错误返回给模型让它自行纠正。

设计思考：为什么另建工具而不是给旧工具加 workflow 参数？
→ ① 每个工作流只挂自己的提交工具，另一个工具模型**根本看不见**（最小权限）；
② `interrupt_on` 按工具名配置，两个工具各自被 HITL 闸住。

- [ ] 测试：合法三值都能提交、非法值抛 ValidationError（参考 `RenewalToolTests`）
- [ ] 注意调用被 `@tool` 装饰后的函数要用 `.invoke({...})`，不能直接 `f(...)`

## Step 6：`agent.py` —— 双工作流装配（本次最大的一个文件）

1. 写 `RENEWAL_SUPERVISOR_PROMPT`：**抄准入协议的骨架**（规划→委派→交叉验证→报告→HITL），
   只换三个业务锚点：政策文件 `/policies/vendor-renewal.md`、报告路径
   `/reports/{供应商}/renewal-report.md`、提交工具 `submit_renewal_decision`、
   决定词表 renew/conditional-renew/no-renew。
   **保留**风险/证据分离、≥4 条证据路径、按域分节这些条款——CLI 校验器和
   四个评估器对两种工作流一视同仁，报告结构相同分数才可比。
2. 建注册表：
   ```python
   WORKFLOW_PROFILES = {
       "onboarding": {"prompt": ..., "submit_tool": submit_onboarding_decision},
       "renewal":    {"prompt": ..., "submit_tool": submit_renewal_decision},
   }
   ```
3. `build_vendor_guard(settings=None, *, workflow="onboarding")`：
   - 开头 fail-fast：`workflow not in WORKFLOW_PROFILES` 就 `raise ValueError`
     （装配时报错，别让模型拿着错协议跑半程）
   - `system_prompt` 和 `tools=[submit_tool]` 从 profile 取
   - `interrupt_on={submit_tool.name: {...}}` —— 用 `.name` 动态生成键，
     换了工具 HITL 闸门自动跟着换，不会脱节

- [ ] 测试：renewal profile 绑定了正确的 prompt/tool；未知 workflow 立刻报错
  （参考 `WorkflowAssemblyTests`，注意这些测试不真正 invoke 模型）

## Step 7：`subagents.py` —— 一行微调

legal-auditor 的 system_prompt 原来写死 `vendor-onboarding.md`，
改成"按任务对应的政策（准入用 vendor-onboarding.md，续约用 vendor-renewal.md）"。
其余三个专家的 prompt 不涉及具体政策文件，不用动。

## Step 8：`cli.py` —— --workflow 开关

按"差异收敛成数据 + 纯函数"的思路做，避免 if/else 散落：

1. `WORKFLOW_REPORT_FILENAMES = {"onboarding": "onboarding-report.md", "renewal": "renewal-report.md"}`
2. `_workflow_report_filename(workflow)`：查表，KeyError 转 ValueError
3. `_build_task_message(workflow, vendor, report_date_iso)`：生成发给主管的任务书
   （续约版要点名 `/policies/vendor-renewal.md`、"若建议续约或有条件续约则提交审批"）。
   注意日期是**参数传入**，函数不读系统时钟——同输入同输出，才好测。
4. `main()` 里：
   - `parser.add_argument("--workflow", choices=sorted(WORKFLOW_REPORT_FILENAMES), default="onboarding")`
     —— choices 让 argparse 在解析层就拒绝拼错值
   - `thread_id` 加中缀：`vendor-novapay-renewal-001`（准入续约是两条独立会话，
     LangSmith 按 thread_id 检索时不能混）
   - 把 workflow 传给 `build_vendor_guard(...)`、`build_run_config(...)`、
     审批记录（"准入建议"/"续约建议"的措辞用 `"续约建议" if workflow == "renewal" else "准入建议"`）

- [ ] 测试：文件名查表、两种任务书用词正确（参考 `CliHelperTests`）

## Step 9：`observability.py` —— Trace 打标

`build_run_config(..., workflow="onboarding")` 加参数，把写死的
`"workflow:onboarding"` tag 和 `"workflow": "vendor-onboarding"` metadata
改成 f-string 插值。之后在 LangSmith 里用 `workflow:renewal` 过滤就只看续约运行。

- [ ] 测试：renewal 时 tags/metadata 正确、默认仍是 onboarding（参考 `RunConfigWorkflowTests`）

## Step 10：`findings_export.py`（进阶，可最后做）

问题：`/workspace/findings/` 走 StateBackend，只活在线程状态里，进程一退就没了；
但作业验收要求**提交四份专业发现文件**。
解法：不改 Backend（会破坏评估隔离），而是运行结束后由 CLI 把状态里的 findings
**导出一份拷贝**到 `reports/{供应商}/findings/`。

新建模块，两个函数：
- `_content_to_bytes(data)`：files 状态通道里的内容有三种历史格式
  （dict/FileData、list[str] 按行、裸 str），统一转 bytes
- `export_findings(state_values, destination) -> list[Path]`：
  遍历 `state_values["files"]`，挑出 findings 前缀下的路径写盘。
  注意坑：CompositeBackend 路由时会**剥掉 `/workspace/` 前缀**，
  所以状态里的键可能是 `/findings/security.md`——两种前缀都要认。

CLI 的 main() 里在报告校验之后调用它。

- [ ] 测试全部用假 state 字典，不碰模型（参考 `test_findings_export.py` 六个用例）

## Step 11：交互式验证（跑真模型）

```bash
uv run vendor-guard NOVAPAY --workflow renewal
```

要验证三件事（作业 15.3 第 6、7 条）：

1. **拒绝路径**：进入 Interrupt 后输入 n → 提交工具未执行、审批表记录"未批准"
2. **批准路径**：同一 `thread_id` 重跑进入 Interrupt 后输入 y → 从断点恢复、提交执行
3. **权限攻击**：口头要求 Agent 修改 `/policies/vendor-renewal.md` → Backend 拒写、文件不变

截图：测试全过、Agent 运行 + HITL、LangSmith Trace
（Trace 里要能看到根运行、四个子 Agent、工具调用、`vendor:NOVAPAY` tag、
`thread_id` 和 `run_kind` metadata）。

## Step 12：`langsmith_dataset.py` —— 三个 NOVAPAY 样例

照 ACME 三样例的结构（完整流程 / 只分析 / 权限攻击）各写一个 NOVAPAY 版，关键差异：

- `inputs` 里加 `"workflow": "renewal"`（ACME 样例不写这个键 → 默认 onboarding，零改动重跑）
- `required_terms` 追加 `"续约"`（保证报告真在谈续约，不是套准入模板）
- 攻击样例的指令改成篡改 `vendor-renewal.md`

```bash
uv run vendor-guard-create-dataset --dataset vendor-guard-onboarding-v2
```

## Step 13：`langsmith_evaluation.py` —— 评估侧认识 workflow

`workflow = str(inputs.get("workflow", "onboarding"))` —— **`.get` 带默认值**是
v1 老样例不用改就能跑的全部秘密。然后按 workflow 分支三样东西：
报告文件名、禁止调用时点名的工具名（"不得调用 A"≠"可以调用 B"，必须点名对的那个）、
任务书文案；`build_vendor_guard` 传 `workflow=workflow`。

注意：**`evaluators.py` 一行都不用改**——四个评估器全部由数据集 outputs 里的
`required_terms`/`min_evidence_paths`/`expect_interrupt`/`expect_protected_unchanged`
驱动，这就是"评估器写得足够数据驱动，扩展业务时才不用碰"的设计收益。

## Step 14：修改后实验 + 对比

```bash
uv run vendor-guard-evaluate --dataset vendor-guard-onboarding-v2 --experiment-prefix vendor-guard-after-change
```

对比方法（作业 15.4 第 5 条）：
- **只对两次实验共有的 ACME 三样例**比分数 → 回答"老功能有没有改坏"
- NOVAPAY 三样例单独看通过/失败项 → 回答"新功能是否达标"
- 至少展开一个失败/低分样例写清原因

## Step 15：HOMEWORK.md + 证据打包

- `HOMEWORK.md`：环境安装、测试、交互运行、数据集创建、评估命令、
  最终续约建议（参考答案给的是 conditional-renew + 桥接期 + 整改条件）、
  LangSmith Project/Experiment 名称
- `docs/evidence/`：01 测试通过、02 运行+HITL、03 Trace、04 Experiment 四组截图
- 截图前检查不暴露 API Key / .env

---

## 收尾自检（对照课件 16.2）

- [ ] 全部测试通过且不调模型
- [ ] `uv run vendor-guard ACME`（不带 --workflow）行为与改前完全一致
- [ ] 主管没有越权调用四个专家专属工具（看 Trace）
- [ ] 拒绝路径不产生提交、批准路径从 Interrupt 恢复后才提交
- [ ] `/policies/vendor-renewal.md` 攻击后内容不变
- [ ] 两次实验四个评估器分数齐全，能解释每个失败样例
