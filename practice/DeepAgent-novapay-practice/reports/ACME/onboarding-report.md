# ACME 供应商准入评估报告

**报告日期：** 2026-08-02

- **报告日期**：2026-08-02
- **评估对象**：ACME（企业注册表状态：candidate）
- **评估依据**：/policies/vendor-onboarding.md；四域专家发现 /workspace/findings/security.md、/workspace/findings/legal.md、/workspace/findings/finance.md、/workspace/findings/reputation.md；数据室证据 /data-room/ACME/ 全部文件；外部资料源 /fixtures/。

---

## 1. Executive Summary（管理层摘要）

ACME 未触发任何一票否决项：制裁名单无命中（/fixtures/sanctions.json records 为空）；合同草案已含 72 小时泄露通知、终止后 30 天数据删除与分包商同等责任条款（/data-room/ACME/contract-draft.md 第 5-7 行）；渗透测试无未整改 Critical 漏洞（/data-room/ACME/pentest-report.md）；财务数据两年一致、受益所有人已验证（/fixtures/vendor_registry.json）。

但存在三类主要问题，支撑 **medium 总体风险 → 有条件准入（conditional）** 的结论：

1. **安全（medium）**：渗透测试 PT-02（medium，部分安全响应头缺失）整改计划完成日为 2026-08-01，截至本报告日 2026-08-02 现有资料**不存在整改完成并通过复测的证据**，按未整改 medium 处理；问卷中的 MFA、TLS 1.2+、AES-256、ISO 27001 等控制声明均无独立佐证（自述待验证）。
2. **法务（medium）**：合同缺失“严重事件临时审计权”条款，审计频率（每两年一次）与通知期（提前 30 天）偏松，责任上限（过去 12 个月服务费）未明确是否排除数据泄露/合规责任——均为可在 30 天内修订的谈判点，非一票否决。
3. **声誉/运营（medium）**：2026-02-18 某地区子公司就加班记录问题与劳动监管机构达成整改协议（已和解，监管公告来源）；2025-11-03 员工邮箱钓鱼事件已关闭且无客户数据外泄；注册表显示近 24 个月争议 2 起、逾期交付率 8%，需持续监控。

**建议决定：有条件准入（conditional）**。30 天内完成整改与补证后于 2026-09-01 复审。

---

## 2. 专业域风险等级

| 专业域 | 风险等级 | 证据状态 | 关键依据 |
|---|---|---|---|
| 安全 | **medium** | 已验证（渗透报告）+ 自述待验证（问卷） | PT-02 未整改；控制声明无佐证 |
| 法务 | **medium** | 已验证为主 | 临时审计权缺失、审计权限制、责任上限待明确 |
| 财务 | **low** | 已验证（指标计算）+ 缺失（部分字段） | 流动比率 1.23-1.29、资产负债率 57.6%-59.0%、现金流为正；供应风险关注项 medium（逾期 8%、争议 2 起） |
| 声誉/舆情 | **medium** | 已验证（单一来源） | 劳动监管整改协议（已和解）、钓鱼事件（已关闭） |
| **总体** | **medium** | — | 未触发一票否决；存在可在 30 天内整改的问题 → conditional |

---

## 3. 风险清单（风险等级 / 证据状态 / 证据位置）

### 3.1 安全域

| # | 风险项 | 风险等级 | 证据状态 | 证据位置 |
|---|---|---|---|---|
| S-1 | PT-02 部分安全响应头缺失，整改计划 2026-08-01 完成；截至 2026-08-02 无完成/复测证据，按未整改 medium 处理 | medium | 已验证（整改状态）/ 冲突（计划完成 vs 无完成证据） | /data-room/ACME/pentest-report.md（测试日期 2026-04-12）；/workspace/findings/security.md F-01 |
| S-2 | PT-01 旧版管理接口缺速率限制（high）已于 2026-04-20 修复并复测 | low（当前） | 已验证 | /data-room/ACME/pentest-report.md；/workspace/findings/security.md F-02 |
| S-3 | 问卷自述控制：生产管理员 MFA、季度权限复核、24 小时离职停用 | low（暂评） | 自述待验证 | /data-room/ACME/security-questionnaire.md；/workspace/findings/security.md F-04 |
| S-4 | 问卷自述数据保护：TLS 1.2+、AES-256、密钥轮换 180 天；受 S-1 影响传输安全加固不足 | medium | 自述待验证 | /data-room/ACME/security-questionnaire.md；/workspace/findings/security.md F-03 |
| S-5 | 事件响应：桌面演练 2025-08-15（自述）；2025-11-03 员工邮箱钓鱼事件已关闭、无客户数据外泄（外部记录）；合同含 72 小时通知条款 | low | 自述待验证 + 已验证 | /data-room/ACME/security-questionnaire.md；/data-room/ACME/contract-draft.md；/fixtures/security_incidents.json；/workspace/findings/security.md F-05 |
| S-6 | ISO 27001 自述有效期至 2027-03-31，无证书副本与年度审计报告 | low（暂评） | 自述待验证 | /data-room/ACME/security-questionnaire.md；/workspace/findings/security.md F-06 |

安全域总体：**medium**（存在未整改 medium，且多项关键控制为自述待验证，不得为 low）。

### 3.2 法务域

| # | 风险项 | 风险等级 | 证据状态 | 证据位置 |
|---|---|---|---|---|
| L-1 | 制裁名单命中 | low（无命中） | 已验证 | /fixtures/sanctions.json（records 为空）；/workspace/findings/legal.md |
| L-2 | 数据泄露通知（72h）、数据删除（30 天）、分包商同等责任条款已写入 | low | 已验证 | /data-room/ACME/contract-draft.md 第 5-7 行 |
| L-3 | 审计权每两年一次且提前 30 天通知 | medium | 已验证（谈判点） | /data-room/ACME/contract-draft.md 第 10-11 行；/workspace/findings/legal.md 3.2 |
| L-4 | 缺失“严重事件临时审计权”条款 | medium | 已验证（缺失） | /data-room/ACME/contract-draft.md 第 17 行（缺失节）；/workspace/findings/legal.md 3.3 |
| L-5 | 责任上限为过去 12 个月服务费，未明确是否排除数据泄露/合规责任 | medium | 已验证（待明确） | /data-room/ACME/contract-draft.md 第 12 行；/workspace/findings/legal.md 3.2 |
| L-6 | 受益所有人 | low（已验证） | 已验证 | /fixtures/vendor_registry.json（beneficial_owner_verified=true）；/workspace/findings/legal.md |

法务域总体：**medium**。一票否决项均未触发（/workspace/findings/legal.md 第 2 节）。

### 3.3 财务域

| # | 风险项 | 风险等级 | 证据状态 | 证据位置 |
|---|---|---|---|---|
| F-1 | 流动比率：2024=1.29、2025=1.23（≥1.0，未触发阈值） | low | 已验证（计算） | /data-room/ACME/financials.csv；/workspace/findings/finance.md |
| F-2 | 资产负债率：2024=57.6%、2025=59.0%（<80%，未触发阈值） | low | 已验证（计算） | /data-room/ACME/financials.csv；/workspace/findings/finance.md |
| F-3 | 经营现金流 +12M（2024）→ +9M（2025），仍为正但同比 -25% | low（趋势关注） | 已验证 | /data-room/ACME/financials.csv；/workspace/findings/finance.md |
| F-4 | 履约表现：逾期交付率 8%（>5% 容忍线）、近 24 个月争议 2 起 | medium（供应风险关注） | 已验证 | /fixtures/vendor_registry.json（late_delivery_rate=0.08, disputes_24m=2）；/workspace/findings/finance.md |
| F-5 | 缺失字段：收入集中度、应收账龄、债务到期结构、EBITDA/利息覆盖 | unknown | 缺失（未补造数字） | /workspace/findings/finance.md 第 4 节 |

财务域总体：**low**（核心偿付指标未触发任何阈值；缺失字段不改变可评估的偿付结论，但 F-4 履约项需纳入整体运营监控）。

### 3.4 声誉/舆情域

| # | 风险项 | 风险等级 | 证据状态 | 证据位置 |
|---|---|---|---|---|
| R-1 | 2026-02-18 某地区子公司加班记录问题与劳动监管机构达成整改协议，状态 settled（已和解） | medium（已解决，影响有限） | 已验证（监管公告，单一来源） | /fixtures/adverse_news.json；/workspace/findings/reputation.md |
| R-2 | 2025-11-03 员工邮箱钓鱼攻击，未发现客户数据外泄，状态 closed | low | 已验证（企业披露） | /fixtures/security_incidents.json；/workspace/findings/reputation.md |

声誉域总体：**medium**（无未决重大负面事件；R-1 因监管机构正式介入暂定 medium，无后续违规可下调为 low）。

---

## 4. Unknown Items（未知项）与待补材料

| 未知项 | 证据状态 | 缺口说明 |
|---|---|---|
| 收入集中度、应收账龄、债务到期结构、EBITDA/利息覆盖 | 缺失 | 财务文件与注册表均未提供（/workspace/findings/finance.md） |
| 劳动整改协议罚款金额与具体条款 | 缺失 | 监管公告未披露（/workspace/findings/reputation.md） |
| 未决诉讼、刑事或进一步调查 | 缺失 | 现有资料未涉及 |
| 主流媒体独立报道 | 缺失 | 仅监管公告与企业披露，无独立媒体来源 |
| ISO 27001 证书、MFA/密钥轮换/权限复核日志、桌面演练纪要 | 缺失（独立佐证） | 问卷自述无佐证（/workspace/findings/security.md） |

**待补材料**：①PT-02 整改完成证明与复测报告；②ISO 27001 证书副本及认证范围、年度第三方审计报告；③MFA 配置与日志、密钥轮换记录、权限复核与离职停用日志；④桌面演练纪要；⑤收入集中度、应收账龄、债务到期表、经营现金流下滑原因说明；⑥劳动整改协议完成证明；⑦分包商清单及筛查记录。

---

## 5. 证据冲突与处理方式

| # | 冲突/不一致 | 处理方式 |
|---|---|---|
| C-1 | PT-02 状态：渗透报告标注“整改中，计划 2026-08-01 完成”，但截至报告日 2026-08-02 无整改完成或复测证据 | 从严按**未整改 medium** 处理；列入整改条件要求复测证明（/data-room/ACME/pentest-report.md；/workspace/findings/security.md F-01） |
| C-2 | 渗透测试发现“旧版管理接口”与问卷声明“生产管理员启用 MFA”的覆盖范围潜在不一致 | 暂按自述待验证处理，需验证旧版接口是否纳入 MFA 与加固范围（/workspace/findings/security.md 第 5 节） |
| C-3 | 问卷自述（ISO 27001、TLS/AES-256、密钥轮换）无独立佐证 | 按政策不标 unknown，标“自述待验证”并降低置信度（55%-65%），要求补证（/workspace/findings/security.md；/policies/vendor-onboarding.md 第 11 条） |
| C-4 | 财务指标健康（low）与运营关注项（逾期 8%、争议 2 起，medium）并存 | 财务域按阈值评 low，运营/供应风险单列 medium 关注，纳入整体监控（/workspace/findings/finance.md） |

无合同条款间相互冲突；无制裁命中；无财务造假迹象。

---

## 6. 最终建议、整改条件与复审日期

**最终建议：有条件准入（conditional）**——未触发一票否决项，但存在可在 30 天内整改的问题（/policies/vendor-onboarding.md 风险等级表）。

**整改条件（30 天内，即 2026-09-01 前）：**

1. 完成 PT-02（安全响应头）整改并通过复测，提交复测报告。
2. 合同修订（/data-room/ACME/contract-draft.md）：新增严重事件临时审计权条款；审计频率改为每年一次；审计通知期缩短并对严重事件豁免；责任上限明确排除数据泄露/合规责任或上调。
3. 补交 ISO 27001 证书副本、年度第三方审计报告、MFA/密钥轮换/权限复核/离职停用日志、桌面演练纪要。
4. 补交收入集中度、应收账龄、债务到期结构及经营现金流下滑原因说明。
5. 提供劳动整改协议完成证明；对逾期交付率（8%）与近 24 个月争议（2 起）建立月度监控，并纳入持续合规监控。

**复审日期：2026-09-01**（整改与补证完成后复审；届时安全域 PT-02 复测通过且控制声明获得佐证后，总体风险方可评估下调）。

---

*本报告由供应商准入总协调人基于四域专家发现（/workspace/findings/security.md、legal.md、finance.md、reputation.md）与原始证据（/data-room/ACME/、/fixtures/）交叉验证生成。人工审批记录由审批系统在审批完成后追加，本报告不预先填写。*

<!-- vendor-guard-approval:741d713f-4a7e-4996-aae1-7e0669381dc6 -->
## 人工审批记录

| 字段 | 内容 |
|---|---|
| 审批记录 ID | 741d713f-4a7e-4996-aae1-7e0669381dc6 |
| 供应商 | ACME |
| 建议准入决定 | conditional |
| 人工处理结果 | 同意执行提交 |
| 人工处理时间 | 2026-08-02T17:29:48+08:00 |
| 操作人（本机账户，未经身份认证） | meish |
| 工作流线程 | vendor-acme-001 |
| 提交状态 | 提交工具已执行 |
| LangSmith Trace | https://smith.langchain.com/o/e466ebc5-6616-4d34-ac63-65ad073bb79b/projects/p/6b1f4e7d-880f-43dc-8a0a-b26075583c50/r/019fc1ca-17a1-7ca1-9518-3f67da93a8bd?poll=true |
