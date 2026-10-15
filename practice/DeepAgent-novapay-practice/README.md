# VendorGuard 供应商准入尽调战情室

这是《Deep Agents 核心理论与能力边界》的配套代码项目。

项目使用 Supervisor Agent（主管智能体）协调安全、法务、财务和舆情四个 Subagent（子智能体），读取本地资料室，生成证据可追溯的供应商准入报告，并在提交决定前触发 Human-in-the-loop（人在回路）审批。LangSmith 用于追踪执行过程和运行离线评估。

## 环境要求

- Python 3.11+
- UV
- 支持 Tool Calling（工具调用）的模型
- 对应模型供应商的 API Key
- LangSmith 账户与 API Key（仅在启用 Trace 或评估实验时需要）

## 安装

### Windows PowerShell

```powershell
uv sync
if (-not (Test-Path .env)) { New-Item .env -ItemType File }
```

### Linux / macOS

```bash
uv sync
touch .env
```

编辑 `.env`，填写 DeepSeek API Key。模型和 LangSmith 的所有凭证都由项目根目录的 `.env` 加载，不在代码中硬编码：

```dotenv
DEEPSEEK_API_KEY=你的DeepSeek密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL_NAME=deepseek-v4-flash
DEEPSEEK_ANSWER_THINKING=true

LANGSMITH_TRACING=true
LANGSMITH_API_KEY=你的LangSmith密钥
LANGSMITH_PROJECT=vendor-guard-course
APP_ENV=local
```

## 运行

以下命令在 Windows、Linux 和 macOS 中相同：

```bash
uv run vendor-guard ACME
```

也可以直接运行模块：

```bash
uv run python -m vendor_guard.cli ACME
```

CLI 会显示 Trace 是否开启。开启后，根运行名为 `vendor-guard-interactive`，并带有供应商、线程、环境和工作流元数据。示例配置默认隐藏重复的输入状态、保留输出，避免 DeepAgents Trace 过大。

## LangSmith 数据集与离线实验

首次创建教学数据集：

```bash
uv run vendor-guard-create-dataset
```

运行离线回归实验：

```bash
uv run vendor-guard-evaluate --experiment-prefix vendor-guard-baseline
```

实验默认串行执行，以控制模型并发和速率限制。每条样例都在独立临时沙箱中
运行：复制 `data-room`、`policies`、`skills` 和 `fixtures`，但不复制本地
`reports`。评估报告内容会上传到 LangSmith，沙箱随后自动清理，因此不会读取、
覆盖交互运行的报告，也不会在样例之间互相污染。评估在 HITL 中断处停止，
不会自动批准提交工具。

## 纯业务层测试

测试不调用模型，也不需要 API Key：

```bash
uv run python -m unittest discover -s tests -v
```

## 教学限制

- 外部查询使用本地 Fixture（固定测试数据），不是生产接口。
- `InMemoryStore` 与 `InMemorySaver` 仅适合本地演示。
- `FilesystemBackend` 只适合受控本地环境，不应用于面向公网的 Web 服务。
- 异步子 Agent 当前不在主流程中，避免把 Preview（预览能力）引入基础实验。
- 教学材料全部为虚构数据。真实合同、财务和个人信息进入 Trace 前必须按组织策略脱敏，必要时关闭输入输出记录或条件追踪。

## 配套文档

- [VendorGuard 项目实战讲解](../02-VendorGuard项目实战讲解.md)
- [LangSmith 基础与 VendorGuard 可观测评估实战](../03-VendorGuard项目的LangSmith可观测与评估.md)
