# 代码阶段与环境操作

网页文章和教学代码在同一个项目中管理，教学代码位于`project/`。解压课件后双击`index.html`即可离线阅读，源码阅读器显示阶段名称、Git tag与提交编号；文章中的代码引用进入对应阶段。执行本页开发实验时，在`project/`中操作，切换代码分支后网页继续使用固定源码。

## 课程与代码阶段

| 课程 | 分支 | 代码变化 | 主要验证 |
| --- | --- | --- | --- |
| 第一课 | `course/00-handover` | 接手时的业务、授权、LangGraph 工具循环、MySQL 进度、预算与恢复 | 教学组件检查与业务基线 |
| 第一课 | `course/01-business-change` | 审批提醒配置、确认时间快照、唯一通知与提醒 worker | 时间、权限、修订、并发与幂等 |
| 第二课 | `course/02-parallel-agents` | OrderAgent 与 KnowledgeAgent 的独立模型决策、工具范围和并行协调 | 角色权限、来源版本与真实模型样本 |
| 第二课 | `course/03-state-consistency` | 结果快照、显式 reducer、稳定排序、线程结果交接 | LangGraph、真实线程与 MySQL 竞争 |
| 第二课 | `course/04-durable-execution` | 分支操作摘要、已完成结果复用、父租约检查 | 实际子进程终止、自然租约到期与恢复 |
| 第三课 | `course/05-data-retrieval-performance` | 订单分页查询及索引实验，结合已有检索能力分析全路径 | 真实查询计划、限定负载与权限 |
| 第四课 | `course/06-context-model-performance` | 完整历史轮次选择、必要查询结果预算、模型连接复用 | 输入完整性、连接行为与受限模型样本 |
| 第四课 | `course/07-streaming-response` | 模型文本增量事件、临时内容与最终消息、取消及续传、专业角色输入预算 | 真实事件、状态变化、计量与流式模型样本 |
| 第五课 | `course/08-deployment-operations` | 发布前检查、服务停止恢复、备份恢复演练 | 真实教学服务和受控进程 |
| 第五课 | `course/09-course-delivery` | 完整课程验收、交付清单、版本及验证记录 | 分支、迁移、接口文档和课程入口 |

起始代码已经具有业务权限、幂等处理、执行租约和计量。各阶段从已有能力继续开发，新增内容通过相邻提交的文件变化核对。源码中的历史验证记录保留原日期及条件，重新运行实验时保存对应记录。

## 环境依赖

运行开发实验需要Git、Python 3.12、uv、Docker Compose和PowerShell 7。阅读网页及源码无需安装这些工具。CPU检索实验使用实际BGE-M3与Milvus，首次下载模型和准备镜像需要网络及磁盘空间。环境参数见教学代码`docs/course/environment.md`。

完整项目已包含`project/`。收到网页压缩包的学员可以通过课程目录下载源码，或在课件根目录用自带Git历史建立教学代码：

```powershell
git clone -b course/09-course-delivery ./downloads/zhifu-course.bundle ./project
```

进入教学代码目录，安装固定依赖：

```powershell
cd project
uv sync --frozen
git status --short
git branch --list 'course/*'
```

代码阶段与环境名称分别管理。`git switch`选择业务代码；`environment.ps1 -Stage`选择Compose project、数据库卷、向量集合及运行配置。每个阶段使用新的环境名称，例如代码`course/00-handover`使用`00-classroom`，代码`course/01-business-change`使用`01-classroom`，后续依次使用`02-classroom`至`09-classroom`。固定源码链接仍使用`00-handover`等代码阶段名称。

首次启动起始代码的独立环境：

```powershell
git switch course/00-handover
. .\scripts\course\environment.ps1 -Action Start -Stage 00-classroom `
  -PythonExecutable .venv\Scripts\python.exe -ModelCache .work\models
```

已有`00-handover`环境的数据库已经升级到后续迁移，初始阶段代码使用独立的`00-classroom`环境。保留已有数据卷。服务端口固定，同一台机器每次运行一个教学环境；启动前停止当前教学环境。测试创建独立租户并清理对应数据。模型采样仅在明确配置凭据和次数上限后执行。

## 切换阶段

以第一课到第二课为例，当前 PowerShell 位于教学代码目录：

```powershell
. .\scripts\course\environment.ps1 -Action Stop -Stage 01-classroom
git status --short
git switch course/02-parallel-agents
. .\scripts\course\environment.ps1 -Action Start -Stage 02-classroom `
  -PythonExecutable .venv\Scripts\python.exe -ModelCache .work\models
```

`git status` 应为空。学员自己的修改需要提交到个人练习分支或者复制保存后手动整理，再切换课程分支。环境 Start 自动应用当前分支迁移，执行就绪检查并记录实际结果；停止命令保留该阶段数据。初次指定的 Python 和模型目录会保存到忽略目录，之后继续使用该阶段时可以省略两个参数。

较早代码使用与其迁移版本对应的数据库。回看旧阶段时，选择只供该阶段使用的独立环境；该环境一旦用于后续阶段迁移，回看时需要创建新的环境名称。`Use`、`Check`、`Stop`与`Start`必须填写同一环境名称。数据库恢复操作使用课程工具指定的独立实例。

## 比较相邻阶段

```powershell
git diff --stat course-02-parallel-agents course-03-state-consistency
git diff course-02-parallel-agents course-03-state-consistency -- src/zhifu/modules/agent_runtime/collaboration.py
git show course-04-durable-execution:src/zhifu/modules/agent_runtime/branch_store.py
```

`--stat`列出修改文件与行数，指定文件路径后可以查看相邻阶段的具体代码变化。沿文章中的请求找到对应函数，同时检查数据保存位置、失败条件和测试断言。每课文章包含实验、作业与参考答案。

## 模型采样与推理部署

生成模型样本必须记录次数上限、实际尝试、输出上限、usage、缓存命中和运行时间；失败及未知结果同样计算。常规并发、数据库、线程、恢复和本地检索实验不发送生成请求。模型采样脚本直接提交协作工具请求时，其结果仅验证该协作路径，不能解释为主模型工具选择准确率。

[项目推理服务部署](./gpu-deployment-lab.html)使用最终教学版本`course-09-course-delivery`接入独立生成服务：两台服务器分别运行一份Qwen3-8B BF16副本，每台一张L40S 48GB，vLLM固定为v0.11.0。材料提供GPU节点、模型网关、环境配置、商家发布与业务检查流程。单序列16384 token、每副本8个序列、每轮4096 token分别限制不同资源；实际响应时间和容量通过受限请求验证。

第四课保留KV cache、continuous batching、chunked prefill、量化和推测解码分析。历史CPU容量练习保留原始假设；部署记录分别保存服务器检查、协议与业务结果、GPU指标和实际调用数量。交付内容为网页课件及配套材料。

## 实验记录与面试准备

每份实验记录包含环境、代码阶段、请求总数、并发、期限、数据规模、实际生成次数、成功和失败结果。解释一个优化时，说明测量对象、为什么选择该修改、指标变化和有效范围。单次模型样本只说明这一次行为，不能推断整体准确率。

实验提交包含自己执行的结果。项目讲解时分别说明个人修改、课程实现和仓库历史记录，附上对应代码阶段与结果文件。
