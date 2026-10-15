## 摘要
Claude Code 的核心是围绕语言模型构建的 Agent Runtime。

模型负责理解任务、选择下一步动作和解释结果。Runtime 负责组织上下文、调用工具、执行权限判断、保存状态、处理失败并控制资源。

---

## 源码仓库
+ 官方项目仓库：[anthropics/claude-code](https://github.com/anthropics/claude-code)
+ 本文源码路径对应的研究分支：[T-Lab-CUHKSZ/claude-code](https://github.com/T-Lab-CUHKSZ/claude-code)

官方仓库用于获取 Claude Code 的正式发行信息。本文出现的 `src/query.ts`、`src/QueryEngine.ts` 等路径，以研究分支的 `main` 分支为准。

`src/...` 是相对于源码仓库根目录的路径。克隆仓库后，`src/query.ts` 位于 `<仓库目录>/src/query.ts`。

克隆命令：

```powershell
git clone https://github.com/T-Lab-CUHKSZ/claude-code.git claude-code
```

---

## 源码定位说明
代码经过版本迭代后，行号可能变化。阅读时应优先搜索符号名，再沿调用关系追踪。

本文中的流程图用于概括源码关系。源码截图用于展示关键实现位置。

## 核心目录
```latex
src/
├─ main.tsx
├─ query.ts
├─ QueryEngine.ts
├─ constants/
│  └─ prompts.ts
├─ coordinator/
│  └─ coordinatorMode.ts
├─ memdir/
│  ├─ memdir.ts
│  └─ memoryTypes.ts
├─ services/
│  ├─ api/
│  │  └─ promptCacheBreakDetection.ts
│  ├─ autoDream/
│  ├─ compact/
│  └─ contextCollapse/
├─ tasks/
├─ tools/
│  ├─ AgentTool/
│  └─ BashTool/
├─ types/
│  └─ permissions.ts
└─ utils/
   ├─ api.ts
   ├─ forkedAgent.ts
   ├─ settings/
   └─ sandbox/
```

## 关键模块索引
| 模块 | 源码位置 | 关键入口 |
| --- | --- | --- |
| Agent 主循环 | `[src/query.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/query.ts)` | `queryLoop`、`needsFollowUp` |
| 推理编排 | `[src/QueryEngine.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/QueryEngine.ts)` | Query 状态与调度 |
| 系统提示词 | `[src/constants/prompts.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/constants/prompts.ts)` | `DANGEROUS_uncachedSystemPromptSection` |
| API 请求 | `[src/utils/api.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/utils/api.ts)` | `splitSysPromptPrefix` |
| 上下文压缩 | `[src/services/compact/](https://github.com/T-Lab-CUHKSZ/claude-code/tree/main/src/services/compact)` | 微压缩、自动压缩、反应式压缩 |
| 上下文折叠 | `[src/services/contextCollapse/](https://github.com/T-Lab-CUHKSZ/claude-code/tree/main/src/services/contextCollapse)` | 折叠操作与持久化 |
| 工具系统 | `[src/tools/](https://github.com/T-Lab-CUHKSZ/claude-code/tree/main/src/tools)` | 工具定义与执行 |
| Bash 安全 | `[src/tools/BashTool/](https://github.com/T-Lab-CUHKSZ/claude-code/tree/main/src/tools/BashTool)` | 安全检查与沙箱选择 |
| 权限类型 | `[src/types/permissions.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/types/permissions.ts)` | `PermissionBehavior` |
| 长期记忆 | `[src/memdir/](https://github.com/T-Lab-CUHKSZ/claude-code/tree/main/src/memdir)` | 记忆索引与类型 |
| 子 Agent | `[src/tools/AgentTool/](https://github.com/T-Lab-CUHKSZ/claude-code/tree/main/src/tools/AgentTool)` | Fork 与调度 |
| Coordinator | `[src/coordinator/](https://github.com/T-Lab-CUHKSZ/claude-code/tree/main/src/coordinator)` | 协调模式 |
| 任务系统 | `[src/tasks/](https://github.com/T-Lab-CUHKSZ/claude-code/tree/main/src/tasks)` | 后台任务状态 |
| 缓存诊断 | `[src/services/api/promptCacheBreakDetection.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/services/api/promptCacheBreakDetection.ts)` | 缓存中断检测 |


## 推荐阅读顺序
```latex
query.ts
  → QueryEngine.ts
  → constants/prompts.ts + utils/api.ts
  → services/compact/
  → tools/
  → types/permissions.ts + tools/BashTool/
  → memdir/ + services/autoDream/
  → tools/AgentTool/ + coordinator/ + tasks/
```

---

## 目录
1. [运行时入口与 Agent 主循环](#1-运行时入口与-agent-主循环)
2. [请求构造与响应处理](#2-请求构造与响应处理)
3. [上下文压缩与折叠](#3-上下文压缩与折叠)
4. [工具定义与执行管线](#4-工具定义与执行管线)
5. [权限、Bash 安全与沙箱](#5-权限bash-安全与沙箱)
6. [会话知识与长期记忆](#6-会话知识与长期记忆)
7. [子 Agent、Coordinator 与任务系统](#7-子-agentcoordinator-与任务系统)
8. [Prompt Cache 与性能机制](#8-prompt-cache-与性能机制)

---

# 1. 运行时入口与 Agent 主循环
## 1.1 源码定位
| 文件 | 符号或区域 | 作用 |
| --- | --- | --- |
| `[src/main.tsx](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/main.tsx)` | 应用入口 | 初始化界面、客户端和运行环境 |
| `[src/query.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/query.ts)` | `queryLoop` | 驱动模型调用与工具反馈循环 |
| `[src/query.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/query.ts)` | `needsFollowUp` | 判断是否需要继续执行 |
| `[src/QueryEngine.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/QueryEngine.ts)` | Query Engine | 协调查询状态与执行过程 |
| `[src/tools/](https://github.com/T-Lab-CUHKSZ/claude-code/tree/main/src/tools)` | 工具目录 | 暴露 Runtime 的外部能力 |


## 1.2 Runtime 的位置
<!-- 这是一张图片，ocr 内容为： -->
![](assets/claude-code-diagrams/runtime-flat.png)

语言模型只生成文本和结构化工具调用。文件读取、命令执行、代码修改和网络访问都由 Runtime 完成。

Runtime 的能力边界由三个层次共同决定：

```latex
模型：提出动作
工具：提供动作
权限：决定动作是否可以执行
```

## 1.3 `queryLoop` 主线
阅读 `[src/query.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/query.ts)` 时，可以同时搜索：

```latex
queryLoop
needsFollowUp
tool_use
tool_result
```

主循环可以压缩为：

```latex
接收用户消息
  → 构造模型请求
  → 消费流式响应
  → 收集 tool_use
  → 判断 needsFollowUp
  → 执行工具
  → 写入 tool_result
  → 进入下一轮
```

<!-- 这是一张图片，ocr 内容为： -->
![](assets/claude-code-source/01-query-loop-source.png)

`tool_use` 是模型提出的动作请求，`tool_result` 是 Runtime 返回的执行观察。两者通过调用 ID 对应。

当响应中不存在待执行工具、用户取消、权限阻断或资源预算耗尽时，循环进入终止状态。

## 1.4 状态机
<!-- 这是一张图片，ocr 内容为： -->
![](assets/claude-code-diagrams/state-flat.png)

源码表面上由循环和条件分支组成，但运行时实际包含准备、模型调用、流式接收、工具规划、权限等待、工具执行、恢复和完成等状态。

显式区分这些状态，可以支持取消、恢复、界面同步和错误追踪。

---

# 2. 请求构造与响应处理
## 2.1 源码定位
| 文件 | 关键符号 | 作用 |
| --- | --- | --- |
| `[src/query.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/query.ts)` | Query 循环 | 构造请求并消费响应 |
| `[src/constants/prompts.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/constants/prompts.ts)` | `DANGEROUS_uncachedSystemPromptSection` | 标记稳定提示词边界 |
| `[src/utils/api.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/utils/api.ts)` | `splitSysPromptPrefix` | 拆分缓存前缀和动态片段 |
| `[src/QueryEngine.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/QueryEngine.ts)` | Query Engine | 管理请求状态和调度 |


## 2.2 一次请求的生命周期
<!-- 这是一张图片，ocr 内容为： -->
![](assets/claude-code-diagrams/lifecycle-flat.png)

工具结果不会直接结束请求。Runtime 会把结果加入消息，再重新整理上下文并调用模型。

这条反馈路径使模型能够根据文件内容、命令输出和错误信息修正下一步动作。

## 2.3 系统提示词的缓存边界
系统提示词由基础规则、环境信息、项目约束、权限模式和当前任务状态等片段组成。

其中一部分长期稳定，另一部分会随请求变化。

```latex
稳定前缀
  ├─ 基础行为规则
  ├─ 工具定义
  └─ 固定项目约束

动态片段
  ├─ 当前环境
  ├─ 临时权限状态
  └─ 当前任务信息
```

<!-- 这是一张图片，ocr 内容为： -->
![](assets/claude-code-source/04-prompt-cache-boundary-source.png)

`prompts.ts` 定义边界，`splitSysPromptPrefix` 消费该边界。片段顺序变化会影响 Prompt Cache。

## 2.4 响应内容
模型响应需要区分文本、工具调用、工具结果和图片等内容块。

工具调用与工具结果必须通过稳定 ID 关联。并发执行多个工具时，这个关联用于防止结果错配。

流式事件一边更新界面，一边累积文本和工具参数。完整工具参数形成后，才进入校验和执行阶段。

---

# 3. 上下文压缩与折叠
## 3.1 源码定位
| 文件 | 关键符号或职责 |
| --- | --- |
| `[src/services/compact/microCompact.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/services/compact/microCompact.ts)` | `COMPACTABLE_TOOLS`，压缩旧工具结果 |
| `[src/services/compact/autoCompact.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/services/compact/autoCompact.ts)` | 阈值计算与摘要预留 |
| `[src/services/compact/compact.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/services/compact/compact.ts)` | `compactConversation` |
| `[src/services/compact/reactiveCompact.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/services/compact/reactiveCompact.ts)` | 上下文超限后的恢复 |
| `[src/services/contextCollapse/operations.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/services/contextCollapse/operations.ts)` | 折叠已消费结果 |
| `[src/services/contextCollapse/persist.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/services/contextCollapse/persist.ts)` | 保存折叠状态 |


推荐阅读顺序：

```latex
microCompact.ts
  → autoCompact.ts
  → compact.ts
  → reactiveCompact.ts
  → contextCollapse/operations.ts
  → contextCollapse/persist.ts
```

## 3.2 微压缩
<!-- 这是一张图片，ocr 内容为： -->
![](assets/claude-code-source/02-micro-compact-source.png)

`microCompact.ts` 不是按消息年龄统一删除内容，而是先判断工具类型、结果位置和保留条件。

旧 Shell 输出、重复搜索结果和已消费的目录列表可以被替换为短占位信息。

用户目标、当前文件内容、未解决错误和后续任务仍依赖的结果需要保留。

## 3.3 自动压缩与反应式压缩
`autoCompact.ts` 在请求接近上下文阈值时触发摘要，并为摘要本身预留输出空间。

`compact.ts` 负责生成可继续执行的会话摘要，而不是普通聊天总结。

`reactiveCompact.ts` 处理模型接口已经返回上下文超限的情况。它执行更激进的压缩，并在有限次数内重新构造请求。

## 3.4 上下文折叠
`contextCollapse` 处理已经完成且不再需要完整展开的工具轨迹。

`operations.ts` 决定哪些内容能够折叠，`persist.ts` 保存折叠状态，使后续请求能够复用折叠结果。

<!-- 这是一张图片，ocr 内容为： -->
![](assets/claude-code-diagrams/compression-flat.png)

压缩的目标不是保留全部历史，而是保留仍会影响下一步决策的信息。

---

# 4. 工具定义与执行管线
## 4.1 源码定位
| 目录或文件 | 主要内容 |
| --- | --- |
| `[src/tools/](https://github.com/T-Lab-CUHKSZ/claude-code/tree/main/src/tools)` | 内置工具定义、参数 Schema 和执行逻辑 |
| `[src/tools/BashTool/](https://github.com/T-Lab-CUHKSZ/claude-code/tree/main/src/tools/BashTool)` | 命令解析、安全检查和沙箱选择 |
| `[src/tools/AgentTool/](https://github.com/T-Lab-CUHKSZ/claude-code/tree/main/src/tools/AgentTool)` | 子 Agent 创建与 Fork |
| `[src/tasks/](https://github.com/T-Lab-CUHKSZ/claude-code/tree/main/src/tasks)` | 长任务与后台任务状态 |


## 4.2 工具的阅读顺序
每个工具都应沿同一条路径阅读：

```latex
工具描述
  → 输入 Schema
  → 参数解析
  → 权限判断
  → 执行函数
  → 结果格式化
```

工具描述和 Schema 决定模型如何提出调用。校验、授权和执行逻辑决定 Runtime 实际接受什么。

只阅读执行函数，会遗漏模型接口和安全边界。

## 4.3 工具类型
| 类型 | 典型能力 | 主要风险 |
| --- | --- | --- |
| 读取工具 | 读文件、搜索、列目录 | 大型输出、越界读取 |
| 修改工具 | 写文件、精确编辑 | 覆盖内容、并发冲突 |
| Shell 工具 | 测试、构建、脚本 | 命令副作用、进程失控 |
| Git 工具 | diff、提交、分支 | 历史或远端状态变化 |
| Agent 工具 | 启动子 Agent | 成本、并发和任务分裂 |


风险不能只按工具名称判断。同一个 Bash 工具执行测试和删除文件时，权限结论完全不同。

## 4.4 工具结果
工具结果需要保留调用 ID、状态、标准输出、错误输出、退出码、耗时和截断状态。

结构化结果让 `queryLoop` 能够区分权限拒绝、参数错误、工具内部错误、外部命令失败和超时。

长输出通常只返回有限片段，并附带原始大小和继续读取信息。这与上下文压缩机制直接相关。

---

# 5. 权限、Bash 安全与沙箱
## 5.1 源码定位
| 文件 | 关键符号 | 作用 |
| --- | --- | --- |
| `[src/tools/BashTool/bashSecurity.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/tools/BashTool/bashSecurity.ts)` | `BASH_SECURITY_CHECK_IDS` | Bash 专项检查集合 |
| `[src/types/permissions.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/types/permissions.ts)` | `PermissionBehavior` | `allow`、`deny`、`ask` |
| `[src/types/permissions.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/types/permissions.ts)` | `PermissionRuleSource` | 记录权限规则来源 |
| `[src/utils/settings/constants.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/utils/settings/constants.ts)` | `SETTING_SOURCES` | 配置层级和优先级 |
| `[src/tools/BashTool/shouldUseSandbox.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/tools/BashTool/shouldUseSandbox.ts)` | `shouldUseSandbox` | 决定是否使用沙箱 |
| `[src/utils/sandbox/sandbox-adapter.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/utils/sandbox/sandbox-adapter.ts)` | 沙箱适配层 | 转换沙箱运行配置 |


## 5.2 Bash 安全检查
<!-- 这是一张图片，ocr 内容为： -->
![](assets/claude-code-source/06-bash-security-source.png)

`bashSecurity.ts` 将不同检查组织为独立 ID。阅读时先定位 `BASH_SECURITY_CHECK_IDS`，再追踪每个检查函数的输入和拒绝条件。

这种结构便于记录具体命中了哪条规则，也便于单独测试和调整。

## 5.3 权限判定链
<!-- 这是一张图片，ocr 内容为： -->
![](assets/claude-code-diagrams/security-flat.png)

源码中的关键顺序是：

```latex
参数校验
  → Bash 静态安全检查
  → 权限规则匹配
  → 必要时请求用户确认
  → 判断是否进入沙箱
  → 执行命令
```

`PermissionRuleSource` 用于区分组织、项目和用户等不同配置来源。上层安全限制不能被下层配置放宽。

## 5.4 沙箱边界
权限系统决定“应该允许什么”，沙箱限制进程“实际上能够做什么”。

`shouldUseSandbox.ts` 负责选择执行模式，`sandbox-adapter.ts` 将上层策略转换为文件、网络和进程等运行限制。

用户确认发生在执行前。确认信息需要包含命令、工作目录和影响范围，否则用户无法判断风险。

---

# 6. 会话知识与长期记忆
## 6.1 源码定位
| 文件或目录 | 关键位置 | 作用 |
| --- | --- | --- |
| `[src/memdir/memdir.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/memdir/memdir.ts)` | 索引限制 | 加载、截断和组织记忆 |
| `[src/memdir/memoryTypes.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/memdir/memoryTypes.ts)` | 记忆类型 | user、feedback、project、reference |
| `[src/skills/loadSkillsDir.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/skills/loadSkillsDir.ts)` | Skill 加载 | 扫描并筛选 Skill |
| `[src/services/autoDream/autoDream.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/services/autoDream/autoDream.ts)` | Auto Dream 入口 | 调度后台记忆整理 |
| `[src/services/autoDream/consolidationPrompt.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/services/autoDream/consolidationPrompt.ts)` | `buildConsolidationPrompt` | 构造整理任务 |


## 6.2 记忆类型
<!-- 这是一张图片，ocr 内容为： -->
![](assets/claude-code-source/05-memory-source.png)

`memoryTypes.ts` 不只定义类型名称，还描述不同信息的保存条件、读取方式和行为约束。

| 类型 | 主要内容 |
| --- | --- |
| user | 用户背景与稳定偏好 |
| feedback | 用户对 Agent 行为的反馈 |
| project | 项目约定与工作状态 |
| reference | 外部资料和资源位置 |


## 6.3 分层加载
<!-- 这是一张图片，ocr 内容为： -->
![](assets/claude-code-diagrams/memory-flat.png)

`memdir.ts` 对索引大小和加载量设置限制。启动时只加载名称、摘要和位置，任务需要时再读取详细内容。

这种设计避免把全部项目知识和历史信息放入每一次模型请求。

## 6.4 Auto Dream
Auto Dream 的调用关系是：

```latex
autoDream.ts
  → 检查空闲状态、时间和会话数量
  → 获取互斥锁
  → 创建独立子 Agent
  → buildConsolidationPrompt
  → 合并、去重并更新记忆文件
```

后台整理维护的是知识结构，不直接承担代码修改任务。

长期记忆只应作为线索。依赖版本、文件位置和分支状态等可实时验证的信息，应以当前仓库结果为准。

---

# 7. 子 Agent、Coordinator 与任务系统
## 7.1 源码定位
| 文件或目录 | 关键符号 | 作用 |
| --- | --- | --- |
| `[src/tools/AgentTool/forkSubagent.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/tools/AgentTool/forkSubagent.ts)` | `FORK_AGENT` | 定义 Fork 子 Agent |
| `[src/utils/forkedAgent.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/utils/forkedAgent.ts)` | `CacheSafeParams` | 保持缓存关键参数一致 |
| `[src/coordinator/coordinatorMode.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/coordinator/coordinatorMode.ts)` | `isCoordinatorMode` | 判断协调模式 |
| `[src/coordinator/coordinatorMode.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/coordinator/coordinatorMode.ts)` | `getCoordinatorSystemPrompt` | 构造协调者提示词 |
| `[src/tasks/types.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/tasks/types.ts)` | `TaskState` | 统一任务状态 |
| `[src/tools/SendMessageTool/](https://github.com/T-Lab-CUHKSZ/claude-code/tree/main/src/tools/SendMessageTool)` | 消息工具 | Agent 间通信 |
| `[src/tools/TaskStopTool/](https://github.com/T-Lab-CUHKSZ/claude-code/tree/main/src/tools/TaskStopTool)` | 终止工具 | 停止后台任务 |


## 7.2 Fork 子 Agent
子 Agent 使用独立消息历史，但可以共享工作区、代码和任务产物。

Fork 模式会继承父 Agent 的必要上下文，并添加子任务目标。它不需要复制父 Agent 的全部中间输出。

<!-- 这是一张图片，ocr 内容为： -->
![](assets/claude-code-source/08-fork-cache-safe-params-source.png)

`CacheSafeParams` 标出父子请求之间必须保持一致的缓存关键参数，包括模型、工具、系统提示词和共享消息前缀等。

## 7.3 Coordinator
<!-- 这是一张图片，ocr 内容为： -->
![](assets/claude-code-diagrams/coordination-flat.png)

Coordinator 负责拆分任务、维护依赖、控制并发、接收结果和统一验证。

<!-- 这是一张图片，ocr 内容为： -->
![](assets/claude-code-source/10-coordinator-mode-source.png)

`coordinatorMode.ts` 表明，协调模式主要通过工具集合和系统提示词改变行为，而不是替换整套 Agent Loop。

## 7.4 Task 与消息
<!-- 这是一张图片，ocr 内容为： -->
![](assets/claude-code-source/11-task-mailbox-source.png)

`TaskState` 使用联合类型表示不同任务状态。具体任务实现位于 `src/tasks/` 的不同目录中。

Agent 间通信通过独立消息工具完成。消息只传递任务状态、依赖通知、结果和警告，不共享完整消息历史。

任务停止也由独立工具处理，使后台任务能够被 Runtime 跟踪和回收。

---

# 8. Prompt Cache 与性能机制
## 8.1 源码定位
| 文件 | 关键符号 | 作用 |
| --- | --- | --- |
| `[src/constants/prompts.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/constants/prompts.ts)` | 缓存边界标记 | 定义稳定区结束位置 |
| `[src/utils/api.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/utils/api.ts)` | `splitSysPromptPrefix` | 切分稳定前缀 |
| `[src/utils/forkedAgent.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/utils/forkedAgent.ts)` | `CacheSafeParams` | 保证 Fork 参数一致 |
| `[src/services/api/promptCacheBreakDetection.ts](https://github.com/T-Lab-CUHKSZ/claude-code/blob/main/src/services/api/promptCacheBreakDetection.ts)` | 状态比较 | 识别缓存中断原因 |


## 8.2 稳定前缀
模型请求中的基础规则、工具定义、模型配置和固定项目约束可以组成稳定前缀。

当前用户消息、最新工具结果和临时权限状态属于动态区域。

```latex
[稳定系统提示词][稳定工具定义][共享消息前缀][当前动态消息]
```

工具排序、提示词片段顺序、默认参数或共享消息前缀发生变化，都可能导致缓存中断。

## 8.3 缓存中断检测
<!-- 这是一张图片，ocr 内容为： -->
![](assets/claude-code-source/09-cache-break-detection-source.png)

`promptCacheBreakDetection.ts` 保存上一轮关键状态，再逐项比较系统提示词、工具 Schema、模型、思考配置和消息前缀。

它的作用不是实现缓存，而是解释为什么原本可复用的前缀发生了变化。

## 8.4 Fork 与缓存
子 Agent 继承父 Agent 的稳定前缀，可以减少重复处理公共上下文。

这也是 `CacheSafeParams` 必须单独定义的原因：父子 Agent 的关键参数如果不一致，Fork 后的请求无法安全复用缓存。

工具输出截断和上下文压缩同样影响缓存。压缩如果改写了稳定前缀，后续请求会重新建立缓存。

---

# 结语
Claude Code 的源码主线可以概括为：

```latex
queryLoop 调用模型
  → 模型产生 tool_use
  → Runtime 校验权限并执行工具
  → tool_result 返回 queryLoop
  → 上下文压缩、状态持久化和缓存机制维持长期运行
```

`query.ts` 是整套系统的主干。工具、安全、压缩、记忆、子 Agent 和缓存模块都围绕这条循环提供能力或约束。

阅读源码时，应始终追踪三个问题：

1. 当前状态由哪个模块持有；
2. 模型输出在哪一步转化为真实操作；
3. 工具结果如何重新进入下一轮模型请求。

沿着这三条线索，可以把 Claude Code 从复杂目录还原为一条可追踪的 Agent Runtime 执行链。

