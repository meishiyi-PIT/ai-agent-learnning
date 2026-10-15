---
name: ocp-docs-source
description: OceanBase OCP 官方文档的可抓取来源（GitHub ocp-doc 仓库 + 文档页 index.md），以及本地已存副本位置
metadata:
  node_type: memory
  type: reference
  originSessionId: 162246f9-319d-4c27-bfdb-72ae1ea7dd0b
  modified: 2026-10-05T10:15:41.187Z
---

- OCP 文档源码在 GitHub `oceanbase/ocp-doc`，公开分支到 V4.4.0（V4.5.1 页面存在但分支未推）。树：`https://api.github.com/repos/oceanbase/ocp-doc/git/trees/V4.4.0?recursive=1`，正文：`https://raw.githubusercontent.com/oceanbase/ocp-doc/V4.4.0/zh-CN/<path>`。
- 文档中心每页都有 markdown 版：在页面 URL 后加 `/index.md`（如 `https://www.oceanbase.com/docs/common-ocp-1000000007050958/index.md`）。WebFetch 对 oceanbase.com 会被拦，用 curl。
- 已下载 28 篇关键文档到 `C:\workspace\resume-refs\ocp-docs\`（AI 助手、自治服务、可疑 SQL、容量中心、事务/会话诊断、信息采集、预案、巡检、告警、日志/链路、任务中心、操作审计、OpenAPI 调用说明/AK-SK/任务结构、告警通道），全量路径清单在同目录 `_all-doc-paths-V4.4.0.txt`。

**How to apply:** 写简历项目二/四、或讲 OCP 功能时先读本地副本；要新文档按上面 raw 路径拉，不要再爬网页。相关：[[resume-project]]
