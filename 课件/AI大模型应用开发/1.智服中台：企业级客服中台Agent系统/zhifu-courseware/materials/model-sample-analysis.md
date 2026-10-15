# 20 次真实模型调用的 token 与费用分析

本材料使用教学代码仓库 `docs/course/verification/` 下的三个协作记录、一个正文流式记录和两个工具流式记录。六个记录均使用 `deepseek-flash`。每个协作样本实际开始 5 次模型尝试，上限为 6 次；正文流式样本实际开始 1 次，上限为 3 次；每个工具流式样本实际开始 2 次，上限为 3 次。20 次模型尝试的状态均为 `RECEIVED`。

## 样本验证范围

三个协作记录覆盖协作工具节点、两个真实专业模型角色以及主模型汇总。测试直接提交协作工具请求，协作工具选择准确率尚未评测。每个样本的 `elapsed_seconds` 是对应检查的整体耗时，无法从这个字段推导每次模型调用的 TTFT、P95 或持续吞吐。

| 记录 | 模型尝试 | 输入 token | 输出 token | 缓存命中输入 | 缓存未命中输入 | 总 token | 整体耗时 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `collaboration-model.json` | 5 | 4977 | 651 | 640 | 4337 | 5628 | 4.098 秒 |
| `collaboration-durable.json` | 5 | 5004 | 636 | 2688 | 2316 | 5640 | 4.472 秒 |
| `collaboration-context.json` | 5 | 5063 | 729 | 1664 | 3399 | 5792 | 4.584 秒 |
| 协作样本合计 | 15 | 15044 | 2016 | 4992 | 10052 | 17060 | — |
| `streaming-model.json` | 1 | 2422 | 360 | 2176 | 246 | 2782 | 3.101 秒 |
| `streaming-tool-attempt.json` | 2 | 5220 | 235 | 4736 | 484 | 5455 | 3.164 秒 |
| `streaming-tool-model.json` | 2 | 5208 | 248 | 4736 | 472 | 5456 | 2.924 秒 |
| 全部合计 | 20 | 27894 | 2859 | 16640 | 11254 | 30753 | — |

缓存输入已经包含在 `input_tokens` 中。三个协作样本合计缓存输入占比为 `4992 / 15044 ≈ 33.18%`。计算总输入量时不能再次加上缓存输入。所有记录均缺少账单编号与调用时的价格快照，实际账单扣费未知。

流式样本另行验证真实文本生成、持久增量事件和真实 HTTP 断线续传。记录包含 2 次 SSE 连接、7 条文本事件；首次可见文本约 1.741 秒，发送器观察到首个文本约 0.823 秒。两个数值的计时起点和观察位置不同，不能直接作为网络耗时相减。`text_chunks=360` 是文本片段计数，本样本与输出 token 数字相同，其他样本需要按各自 usage 计量。

工具流式记录覆盖主模型生成工具参数、实际订单查询、最终正文与预算结算。`streaming-tool-model.json` 的验收状态为 VERIFIED，记录 1 次工具调用和 3 条最终正文事件。`streaming-tool-attempt.json` 的验收状态为 FAILED，其中 2 次模型调用已经收到 usage，因此计入总次数与费用。

三个协作记录及 `streaming-model.json` 只有相对耗时，没有日历起止时间。两个工具流式记录包含 UTC 起止时间：

| 记录 | `started_at` | `finished_at` | 北京时间 |
| --- | --- | --- | --- |
| `streaming-tool-attempt.json` | `2026-09-25T15:02:14.948805Z` | `2026-09-25T15:02:18.113129Z` | 23:02:14—23:02:18 |
| `streaming-tool-model.json` | `2026-09-25T15:03:25.619891Z` | `2026-09-25T15:03:28.544160Z` | 23:03:25—23:03:28 |

## 2026-09-25 查询的官方价格

DeepSeek 官方中文价格页列出 `deepseek-flash`，对应模型版本为 DeepSeek-V4.1-Flash。每百万 token 的人民币单价如下。[DeepSeek 官方模型与价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)

| 计价项目 | 空闲时段 | 高峰时段 |
| --- | ---: | ---: |
| 缓存命中输入 | 0.02 元 | 0.04 元 |
| 缓存未命中输入 | 1 元 | 2 元 |
| 输出 | 4 元 | 8 元 |

官方定义北京时间周一至周五的 9:00—12:00、14:00—18:00 为高峰时段，中国法定节假日除外；其余时间为空闲时段。两个工具样本的已知时间属于空闲时段；其他 16 次调用按两种时段估算。费用使用这次查询到的价格，实际扣费仍需核对供应商账单。

```text
未命中输入 = input_tokens - input_token_details.cache_read
估算费用 = (未命中输入 × 未命中单价
          + 缓存命中输入 × 缓存命中单价
          + output_tokens × 输出单价) / 1000000
```

| 记录 | 费用估算下限 | 费用估算上限 |
| --- | ---: | ---: |
| `collaboration-model.json` | 0.00695380 元 | 0.01390760 元 |
| `collaboration-durable.json` | 0.00491376 元 | 0.00982752 元 |
| `collaboration-context.json` | 0.00634828 元 | 0.01269656 元 |
| 协作样本合计 | 0.01821584 元 | 0.03643168 元 |
| `streaming-model.json` | 0.00172952 元 | 0.00345904 元 |
| `streaming-tool-attempt.json`，已知空闲时段 | 0.00151872 元 | 0.00151872 元 |
| `streaming-tool-model.json`，已知空闲时段 | 0.00155872 元 | 0.00155872 元 |
| 全部合计 | 0.02302280 元 | 0.04296816 元 |

两个工具样本合计估算费用为 0.00307744 元。其余记录的两列分别采用空闲与高峰单价。实际扣费还需与供应商账单及当时价格核对，赠送余额扣减也会影响充值余额变化。

## 可以复算的 PowerShell 命令

在课件项目的 `project/` 教学代码目录执行。这段命令只读取固定六个 JSON 文件并进行 Decimal 计算，不产生模型调用。输出分别列出两种价目金额；两个工具样本使用 `off_peak_cny`，其他样本保留两档范围。

```powershell
$names = @(
    'collaboration-model', 'collaboration-durable', 'collaboration-context',
    'streaming-model', 'streaming-tool-attempt', 'streaming-tool-model'
)
foreach ($name in $names) {
    $record = Get-Content "docs/course/verification/$name.json" -Raw | ConvertFrom-Json
    [decimal]$inputTokens = 0
    [decimal]$outputTokens = 0
    [decimal]$cachedTokens = 0
    foreach ($attempt in $record.attempts) {
        $inputTokens += $attempt.usage.input_tokens
        $outputTokens += $attempt.usage.output_tokens
        $cachedTokens += $attempt.usage.input_token_details.cache_read
    }
    $missedTokens = $inputTokens - $cachedTokens
    $offPeak = ($missedTokens + $cachedTokens * [decimal]'0.02' + $outputTokens * 4) / 1000000
    [pscustomobject]@{
        sample = $name
        attempts = $record.started_attempts
        input_tokens = $inputTokens
        output_tokens = $outputTokens
        cache_read = $cachedTokens
        cache_miss = $missedTokens
        off_peak_cny = $offPeak
        peak_cny = $offPeak * 2
    }
}
```

## 业务量估算练习

本练习只采用三个协作样本的平均值。假设未来业务保持其输入、输出、缓存比例与 5 次模型尝试，1000 个业务预计需要 5000 次模型尝试、约 5014667 个输入 token、672000 个输出 token。输入中约 1664000 个 token 命中缓存，约 3350667 个 token 未命中缓存。按照未取整的平均值计算，费用约为 6.071947 元或 12.143893 元。流式样本属于另一种执行范围，不加入这组业务平均值。

如果每分钟到达 30 个同类业务，则期望调用量为 150 次/分钟，总 token 为 170600/分钟。额外尝试数量按正常调用的 5% 估算时，期望调用量为 157.5 次/分钟，总 token 为 179130/分钟。规划请求上限时应将次数向上取整，并分别检查供应商对输入、输出和并发的具体限制。

业务估算需要保留以下假设：业务类别比例不变、输入长度分布不变、缓存命中比例不变、专业角色数量不变、没有新增摘要调用、没有新增业务重试。真实流量变化后需要重新采样和计算。预算扣减、重复结算、权限、审批和父运行累计次数上限应继续通过对应真实数据库测试验证。

## 样本结论与测量范围

这些样本可以说明一次协作请求包含多次计费调用，并展示缓存输入的独立计价方法。三份样本的输出长度和缓存量不同，每个阶段只有一个协作样本，无法据此计算持久化固定耗时、多 Agent 加速比、上下文优化节省比例或整体业务准确率。

性能对照需要固定业务数据、prompt、模型版本、输出限制、连接初始状态及缓存条件；分别记录专业角色、主模型和工具调用耗时。调用次数上限、token 上限、最长运行时间需要在执行前写入记录。当前材料复用已有 20 次调用，费用计算过程新增模型调用数量为 0。

## 文件指纹

以下 SHA256 对应本材料读取的原始记录。文件内容变化时需要重新统计，同时更新本材料中的验证范围。

| 文件 | SHA256 |
| --- | --- |
| `collaboration-model.json` | `41bc029f0293b5c8ee0a187c1b67d3a23fc5e11084fefabfc8ddb557c8fe634a` |
| `collaboration-durable.json` | `b29ea5ed969572d754d225e3582e991e60342cea5497dbae69e493d6801111e9` |
| `collaboration-context.json` | `0e1e9a048ce4b153e6f71020bb850381ab2026bf75f1b6491d1c9d31cfc8e94c` |
| `streaming-model.json` | `b28dbf2321def7b89114cdb1beefaad5514b654797fc5897ef920753ca697b9f` |
| `streaming-tool-attempt.json` | `88757c5743759afafd9fd01f4301c430f27985203358add4f35f4329c791bfb8` |
| `streaming-tool-model.json` | `5f43a695bcc24a1e91985d015cead028e3101c222c4a59f5a4fa95da2bbbaccc` |
