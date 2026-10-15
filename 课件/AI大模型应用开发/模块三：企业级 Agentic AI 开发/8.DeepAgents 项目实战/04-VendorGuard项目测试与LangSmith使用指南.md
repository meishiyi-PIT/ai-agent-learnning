本文说明如何安装、运行和测试 VendorGuard，以及如何使用 LangSmith Trace、离线评估和回归对比。

以下命令默认在 `vendor-guard/` 项目根目录执行。

---

## 一、安装项目
项目要求：

+ Python 3.11+
+ UV
+ 可调用的 DeepSeek API Key
+ LangSmith 账户与 API Key（仅在使用 Trace 或离线评估时需要）

进入项目目录并同步依赖：

```powershell
cd vendor-guard
uv sync
```

`uv` 检测到项目源码变化时，可能显示 `Built`、`Uninstalled` 和 `Installed`，这是自动重新安装本地项目的正常输出。

---

## 二、运行供应商准入流程
项目内置虚构供应商 `ACME`，资料位于：

```latex
data-room/ACME/
```

运行完整流程：

```powershell
uv run vendor-guard ACME
```

程序会：

1. 读取供应商资料和准入政策。
2. 调用安全、法务、财务和声誉四个子 Agent。
3. 生成风险报告。
4. 在提交准入决定前进入人工审批。

报告保存到：

```latex
reports/ACME/onboarding-report.md
```

报告日期由 CLI 根据本机日期写入，不采用模型猜测的日期。

### 测试未知供应商
运行：

```powershell
uv run vendor-guard UNKNOWN
```

系统应明确说明资料缺失，不得编造合同、财务、安全或声誉事实，也不得在无证据时直接批准。

---

## 三、人工审批与报告
需要提交准入决定时，终端会显示：

```latex
待人工审批： {'name': 'submit_onboarding_decision', 'args': {...}}
批准执行？[y/N]
```

输入含义：

| 输入 | 结果 |
| --- | --- |
| `y` | 同意执行提交工具 |
| `n` 或直接回车 | 拒绝执行提交，准入建议不提交 |


“审批完成”和“批准执行”是两个概念。输入 `n` 表示人工审批已经完成，但审批结果是不批准执行。

审批完成后，CLI 会在报告末尾写入人工审批记录，包括：

+ 建议准入决定
+ 人工处理结果
+ 带时区的处理时间
+ 本机操作账户
+ 工作流线程 ID
+ LangSmith Trace
+ 提交状态

终端最终状态由 CLI 输出，不采用模型对审批结果的二次解释。

---

## 四、运行本地测试
本地测试不调用模型，也不需要 LangSmith：

```powershell
uv run python -m unittest discover -s tests -v
```

看到以下结尾表示通过：

```latex
OK
```

本地测试主要覆盖：

+ 配置和密钥读取
+ Fixture 数据查询
+ Windows UTF-8 输出
+ 报告日期与风险语义
+ 人工审批审计记录
+ LangSmith 配置和评估器
+ 离线评估沙箱隔离

如果本地测试失败，应先修复错误，再运行完整 Agent 或离线评估。

---

## 五、使用 LangSmith Trace
在 `.env` 中开启：

```plain
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=你的LangSmith API Key
LANGSMITH_PROJECT=vendor-guard-course
LANGSMITH_HIDE_INPUTS=true
LANGSMITH_HIDE_OUTPUTS=false
```

重新运行：

```powershell
uv run vendor-guard ACME
```

终端会显示 Trace 链接。建议先打开链接检查执行过程，再回到终端输入 `y` 或 `n`。

在 Trace 中重点检查：

| 检查点 | 预期 |
| --- | --- |
| 根运行 | `vendor-guard-interactive` |
| 任务规划 | 主管 Agent 创建任务计划 |
| 专业审查 | 四个领域进入对应子 Agent |
| 工具调用 | 子 Agent 只使用授权工具 |
| 发现记录 | 写入 `/workspace/findings/` |
| 报告生成 | 写入 `/reports/{供应商}/onboarding-report.md` |
| 人工审批 | 提交工具执行前出现中断 |


如果链接无法打开，应确认浏览器登录账号有权访问 API Key 所属的 LangSmith Workspace。

---

## 六、创建数据集并运行离线评估
### 创建测试数据集
首次使用时执行：

```powershell
uv run vendor-guard-create-dataset
```

该命令会在 LangSmith 中创建：

```latex
vendor-guard-onboarding-v1
```

数据集保存在 LangSmith 云端，不会生成本地 JSON 文件。数据集已存在时无需重复创建。

内置用例包括：

1. 标准调查并进入人工审批。
2. 只生成报告，不调用提交工具。
3. 拒绝修改受保护政策的权限攻击。

### 运行离线评估
执行：

```powershell
uv run vendor-guard-evaluate --experiment-prefix vendor-guard-baseline
```

参数含义：

| 参数 | 用途 |
| --- | --- |
| `--dataset` | 指定 LangSmith 数据集 |
| `--experiment-prefix` | 指定实验名称前缀 |


示例：

```powershell
uv run vendor-guard-evaluate `
  --dataset vendor-guard-onboarding-v1 `
  --experiment-prefix vendor-guard-baseline
```

每条用例都会在独立临时沙箱中运行。评估只复制输入资料，不复制本地 `reports`，因此不会读取或覆盖手动生成的报告，也不会在用例之间互相污染。

评估完成后，终端会显示实验名称、完成数量和 LangSmith 结果链接。

当前评估器检查：

| 评估器 | 检查内容 |
| --- | --- |
| `report_completeness` | 报告必填概念是否齐全 |
| `evidence_traceability` | 是否引用足够的证据路径 |
| `approval_boundary` | 是否按预期进入或避开审批 |
| `protected_sources_unchanged` | 原始资料、政策和 Skills 是否保持不变 |


离线评估会调用模型并产生 Token 消耗。LangSmith 显示 `$0.00` 可能只是缺少当前模型的价格映射，不代表模型供应商没有计费。

---

## 七、做一次回归对比
回归对比用于判断 Prompt、Skill、工具、代码或模型配置修改后，质量、可靠性和成本是否发生变化。

### 1. 设置修改前配置
下面以“开启和关闭模型思考模式”为例。先在 `.env` 中设置：

```plain
DEEPSEEK_ANSWER_THINKING=true
```

然后运行修改前基线：

```powershell
uv run vendor-guard-evaluate --experiment-prefix vendor-guard-thinking-on
```

记录实验名称、评分、错误、Token 和延迟。

### 2. 修改一个变量
将 `.env` 修改为：

```plain
DEEPSEEK_ANSWER_THINKING=false
```

不要同时修改 Prompt、Skill、工具、Dataset 或 Evaluator，否则无法确认差异是否由思考模式引起。

### 3. 运行修改后实验
```powershell
uv run vendor-guard-evaluate --experiment-prefix vendor-guard-thinking-off
```

`--experiment-prefix` 只是实验名称标签。真正控制思考模式的是 `.env` 中的 `DEEPSEEK_ANSWER_THINKING`。

### 4. 在 LangSmith 比较实验
选择修改前和修改后的两个 Experiment，重点比较：

| 指标 | 判断方式 |
| --- | --- |
| 运行成功率 | 是否出现新增错误 |
| 评估器分数 | 是否有用例降分 |
| 报告内容 | 是否遗漏或出现口径漂移 |
| 工具调用 | 是否调用错误工具或越权 |
| 审批边界 | 应中断和不应中断的场景是否正确 |
| Token | 是否明显增加或下降 |
| 延迟 | P50 和每条用例耗时是否变化 |


对比期间应保持 Dataset 和 Evaluator 不变。否则无法判断变化来自 Agent，还是来自测试标准。

修改后更快但出现错误或降分，仍属于回归。不要只根据 Token 或延迟判断修改成功。

### 5. 恢复原配置
实验结束后，如需继续使用开启思考模式的稳定配置，将 `.env` 改回：

```plain
DEEPSEEK_ANSWER_THINKING=true
```

---

## 八、必要故障排查
### API Key 认证失败
典型错误：

```latex
AuthenticationError: 401
```

检查：

+ `DEEPSEEK_API_KEY` 是否正确、完整且未失效。
+ `DEEPSEEK_BASE_URL` 是否与 Key 匹配。
+ 修改 `.env` 后是否重新启动命令。

### Windows 中文解码错误
项目已内置 UTF-8 重启保护。如果仍出现 GBK 解码错误，可临时执行：

```powershell
$env:PYTHONUTF8="1"
$env:PYTHONIOENCODING="utf-8"
uv run vendor-guard ACME
```

### LangSmith Trace 显示关闭
确认 `.env` 包含：

```plain
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=你的LangSmith API Key
```

### LangSmith 实验出现错误
打开错误用例的 Trace，先查看根运行的 `error`，再定位到失败的子 Agent 或工具调用。

实验有错误时，不要只看平均分。部分评估器可能因为缺失字段的默认值而产生误导性分数。

---

真实业务资料上传 LangSmith 前，应按组织要求脱敏，或关闭相应输入、输出记录。

