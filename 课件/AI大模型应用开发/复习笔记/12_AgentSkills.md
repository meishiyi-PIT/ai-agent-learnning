# Agent Skills 复习笔记
> 对应课件：3.Agent Skills 基础入门.md、4.Agent Skills 工程实战.md

## 一、在知识体系中的位置

学 Skills 之前先接住三根前置线：

- **Prompt（提示词）**：一次性告诉模型"这回要干什么"。
- **Function Calling / Tool**：模型"怎么发起一次外部调用"（见笔记 11）。
- **MCP**：外部能力（文件、数据库、GitHub）"怎么接进来"（见笔记 11）。

**Skills 补的是第四块拼图——"这类任务应该怎么做"。** 它是一份**可被 Agent 按需发现、按需加载的任务执行说明书**（一个目录 + 一个 `SKILL.md`）。四者关系课件总结得极精炼，务必背下：

> **Prompt 管"做什么"，Function Calling 管"怎么调"，MCP 管"怎么连"，Skill 管"怎么做"。**

- **与 MCP 的分工（易混，重点）**：MCP 给的是"能力/工具"（一个会执行的东西），Skills 给的是"做法/流程/经验"（一份会被读的说明书）。一个是"手"，一个是"菜谱"。后面 4.4 详补。
- **本质定位**：Skills 是**上下文注入机制**，不是能力增强。它不改变模型底层能力，只是把项目私有的知识、最佳实践、流程规范，在恰当时机结构化地喂给 Agent。

---

## 二、核心知识点精讲

### 2.1 Skill 是什么：菜谱，不是厨师
课件的类比很到位：Skill 像一本菜谱，写清了洗菜、切菜、油温、调料、火候。但**菜谱自己不会做饭**——真正做饭的是 Agent。所以 Skill 里可以写流程、放脚本，但它不会自己选目标、不会管长期任务、不会判断何时该停、不对业务结果负责。**它是"能力文件"，执行者仍是 Agent。**

一句话本质：**把某类任务的做法、经验、格式和必要脚本，打包成一个可复用的能力文件**（说明书 + 模板 + 示例 + 工具）。

### 2.2 什么任务适合做成 Skill
四个特征全占才划算：**高频重复、一致性要求高、流程已成熟、复杂度适中**（单靠一句 Prompt 难稳定跑通）。反例：一次性小任务、流程还没跑顺的探索性工作——别急着封装。

判断"该写 Prompt 还是该包成 Skill"的黄金问法（课件精华）：
> **"这段话如果某一轮 Agent 没看到，它会不会做出不对的行为？会 → 写 Prompt 常驻；不会 → 包成 Skill 按需加载。"**

所以"用中文回复""你叫小助手""遇到不确定先问我"这类**必须每轮都在**的指令，就该写进常驻 Prompt，不适合做 Skill。

### 2.3 渐进式披露（Progressive Disclosure）—— 本讲的灵魂机制
这是 Skills 最该学透的一点。核心矛盾：**上下文窗口是稀缺资源，塞得多不等于表现好**，信息越多核心规则越容易被稀释。解法是**三层加载，用到才加载**：

| 层级 | 加载时机 | 加载内容 | 体量 |
| --- | --- | --- | --- |
| 广告层 | 启动时 | `name` + `description` | 极短（约几十 token/skill） |
| 指令层 | 命中后 | `SKILL.md` 正文 | 建议 ≤500 行 |
| 资源层 | 执行时 | `references/`、`scripts/`、`assets/` | 按需读 |

这样：启动时 Agent 只知道"有哪些能力可用"（省 token）；命中某个 Skill 才读完整指令；真正执行时才去读参考资料。**50 个 Skill 也只在上下文里常驻 50 行摘要**，这就是它相对"裸 Prompt 全塞进 AGENTS.md"的核心优势。

### 2.4 Skill vs 裸 Prompt 的量化对比
| 维度 | 裸 Prompt | Skill |
| --- | --- | --- |
| 平时占 token | 每轮都占 | 只占一行摘要 |
| 用到时 | 零延迟直接可用 | 多一次读取（约 0.2 秒） |
| 50 个功能 | context 爆炸 | 依然只多几百 token 摘要 |

Skill 额外还带来：**条件加载**（不满足前置条件自动隐藏）、**开关控制**（一行配置禁用）、**可分享**（发社区）、**隔离性**（改 Skill 不动核心 Prompt）。代价只有"多一次 read 的微小延迟"。

### 2.5 标准文件结构
以文件夹为单位，最小形态只要一个 `SKILL.md`：

| 文件/目录 | 必须 | 作用 | Agent 的动作 |
| --- | --- | --- | --- |
| `SKILL.md` | ✅ | 唯一入口 | —— |
| `scripts/` | 可选 | 确定性可执行脚本 | **跑** |
| `references/` | 可选 | 长参考资料，按需读 | **看** |
| `assets/` | 可选 | 模板/素材，套格式 | **填** |

关键规则：`SKILL.md` 必须直接放在 `skills/<skill-name>/` 下，**不能再嵌套**（`skills/my-skill/src/SKILL.md` 是错的）；目录名建议与 skill 名一致，全小写、连字符分隔。

三个可选目录的选用信号：**同一命令 Agent 老写错 → 抽成 script；正文太长影响阅读 → 拆到 references；输出格式不稳定 → 做个 asset 模板。**

### 2.6 SKILL.md 的两段式结构
`SKILL.md = YAML frontmatter（元数据）+ Markdown 正文（指令）`。

```yaml
---
name: processing-pdfs
description: 从 PDF 提取文本和表格、填表、合并文档。处理 PDF 或用户提及 PDF/表单/文档提取时使用。
---
# 正文：何时触发、按什么顺序执行、失败怎么办
```

- **`name`**：唯一标识。≤64 字符，只允许小写字母、数字、连字符（`-`），建议用动名词（`processing-pdfs`、`reviewing-code`）。
- **`description`**：**决定 Agent 何时想到这个 Skill，是最重要的字段。** 三原则：① 包含用户可能说的原话/触发词；② 明确写出不适用场景；③ 简洁（官方硬上限 1024 字符，见第三节）。
- **正文**：真正的指令，只有 Agent 决定用时才读。写"操作手册"不写"科普文"，控制在 500 行内，超了就靠渐进式披露拆分。

### 2.7 正文编写与自由度把控
- **正文别当 README**：README 给人看（背景、安装、特性），Skill 给 Agent 看（何时触发、执行顺序、哪些不做、失败兜底）。
- **最值钱的是项目私有踩坑记录**：如"`users` 表是软删除，所有查询必须加 `WHERE deleted_at IS NULL`"——这种 Agent 推断不出来的信息才该写；通用常识别写，浪费上下文。
- **三级自由度看风险**：高风险（改数据、发请求、部署、迁移、删文件）→ 锁死精确命令、标注不可改；分析/评审/生成草稿 → 给方向、放宽裁量。
- **复杂任务必须有验证点**：用可判定的清单（"每个新函数都有测试""所有测试通过"）串步骤，别让 Agent 一口气跑到底就自称完成。

### 2.8 路由与规模化
Skill 少时靠模型扫 `description` 匹配即可；多了要做**粗召回（向量化取 top-k）→ 精排 → 兜底（分都低时"不选"比"硬选"更安全）**。新 Skill 缺历史 Query，可加触发词提升冷启动命中（课件用的是 `triggers` 字段，见第三节勘误）。规模再大可拆成"注册中心 / 路由引擎 / 加载器 / 上下文装配器"四模块。

### 2.9 在 Claude Code 里用 Skill（工程落地）
- **存放位置**：项目级 `.claude/skills/`（随项目、可提交 Git）、个人全局级 `~/.claude/skills/`（所有项目可用）。
- **两种形态**：简单场景可单文件 `code-review.md`；复杂场景用目录 + `SKILL.md` + `assets/` + `references/`，正文里用 `{baseDir}` 引用 skill 目录内文件。
- **触发控制字段**：`disable-model-invocation: true`（禁自动触发，只能手动 `/技能名`，适合部署/删除等危险操作）、`user-invocable: false`（不在斜杠菜单显示但可自动触发，适合后台辅助技能）。
- **管理**：输入 `/` 或 `/skills` 查看已装 Skill；删除即移除文件夹。

---

## 三、课件勘误与更新

### 已确认

**1. 冷启动用的 `triggers:` 字段 —— 不严谨（字段名不是官方标准）**
- 课件原文（课件2 · 5.2）：用 `triggers:` 列表来提升命中率。
- 问题类型：**不严谨**。概念方向对（补充触发词有用），但 Anthropic 官方 frontmatter 里承担"额外触发词"职责的标准字段叫 **`when_to_use`**，并没有名为 `triggers` 的官方字段；把"何时使用"的信息直接写进 `description` 才是官方主推做法。写给 Claude 用时请用 `when_to_use` 或并入 `description`。
- 来源：[Claude 平台文档 · Agent Skills 概览](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)、[Agent Skills 开放标准 · Specification](https://agentskills.io/specification)

**2. 完整模板里的 `platforms:` 字段 —— 不严谨（非官方标准字段）**
- 课件原文（课件2 · 九、完整模板）：frontmatter 写了 `platforms: - macos - linux`。
- 问题类型：**不严谨**。官方 SKILL.md 除必填 `name`/`description` 外，规范化的可选字段是 `license`、`compatibility`、`metadata`、`allowed-tools` 等；`platforms`、`author`、`version` 不是被官方识别的标准字段（多数实现会当成未知字段忽略或塞进 `metadata`）。作为团队自定义元数据可以放 `metadata` 里，但别当成规范字段。
- 来源：[Agent Skills 开放标准 · Specification](https://agentskills.io/specification)、[anthropics/skills 官方仓库](https://github.com/anthropics/skills)

**3. `metadata: {"openclaw": {...}}` 示例 —— 待核实偏错**
- 课件原文（课件3 · 3.1）：`metadata: {"openclaw": {"requires": {"env": ["STOCK_API_KEY"]}}}`。
- 问题类型：**存疑**。`metadata` 字段本身是官方可选字段，但其中的 `"openclaw"` 命名空间不是 Anthropic 官方约定，我未在官方文档找到该键的来源，疑为某第三方运行时（或课件杜撰的示意名）。列此提醒：这不是通用标准写法，跨平台不保证被识别。（因无法定位权威来源，同时列入下方"待核实"。）
- 来源：官方可选字段见 [Agent Skills 开放标准 · Specification](https://agentskills.io/specification)

**4. `description` 编写建议 "控制在 5 行以内" —— 补充官方硬指标**
- 课件（课件3 · 3.4）只给了"5 行以内"的经验值。补一条可量化的官方上限：**`name` ≤ 64 字符，`description` ≤ 1024 字符**，且 `description` 必须同时包含"做什么（WHAT）+ 何时用（WHEN）"、用**第三人称**写（因为它会被注入系统提示，用"我/你"会干扰 Agent 视角）、避免尖括号 `< >`。
- 问题类型：**更新/补充**（课件说法不算错，只是没给硬数字）。
- 来源：[Claude 平台文档 · Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)、[SKILL.md Frontmatter Reference](https://www.anthropiccertifications.com/courses/introduction-to-agent-skills/skill-frontmatter-reference)

**5. Agent Skills 的发布时间线 —— 补充（课件没写）**
- 事实补充：Anthropic 于 **2025-10-16** 正式发布 Agent Skills，随后于 **2025-12-18** 通过 **agentskills.io** 将其作为**开放标准**开放。这解释了课件里"跨平台（Claude/GPT/Gemini 都能用）"的说法从何而来——它确实在往开放标准走。
- 来源：[anthropics/skills 官方仓库](https://github.com/anthropics/skills)、[Agent Skills 开放标准](https://agentskills.io/specification)

### 待核实

- **"SkillHub / `skillhub install`" 命令行工具**（课件2 · 10.2、11.4）：课件给出 `skillhub install/list/search/update/rollback/outdated` 一整套 CLI。我未找到名为 "SkillHub" 的官方或主流包管理器权威来源，疑为课件为讲解"社区安装"而虚构的示意工具（课件自己也加了"不同平台命令可能不同"的提示）。**当作"概念演示"理解即可，别当成真实存在的命令去装。** 真实生态里更常见的是各平台自带的 skill 目录管理 / 插件市场。
- **附录 C 的平台与数据**（课件3 · 附录C）：SkillsMP.com（50,000+）、Smithery.ai（15,000+）、Claude Plugins（9,736+）等站点名称、网址、技能数量，以及"热门 Skills 排名 Top10"（UniversalCodeReviewer 等具体产品名）——这些具体数字和排名无法逐一核实，且这类榜单时效性极强，**仅作了解，不要引用为事实**。可确认真实存在的官方权威源只有 [github.com/anthropics/skills](https://github.com/anthropics/skills)。
- **`_meta.json` 自动生成文件**（课件2 · 10.2）：依附于上面存疑的 skillhub 工具，同样待核实，非官方规范产物。
- **具体元数据键 `openclaw`**：见勘误第 3 条，未找到权威来源。

---

## 四、课件没讲透的关键点补充

### 4.1 渐进式披露到底"省"在哪——把 token 账算清
课件给了三层架构，但没把"为什么这样能扩展"讲到底。关键在于**只有"广告层"是常驻成本**：启动时每个 Skill 只加载 `name+description`（约几十 token）。假设你有 100 个 Skill，常驻成本 ≈ 100 × 几十 token，几千 token 就打住了；而它们的正文（可能各几百上千 token）**只有命中的那一个**才会被读进来。这就是"能力可以无限堆，上下文却不炸"的根本原因——**把"目录"和"正文"在时间上解耦**。这也是它区别于"MCP 一次性把所有工具 schema 灌进上下文"的地方。

### 4.2 Skills 与 MCP 的分工——最该分清的一对
课件表格给了"Skill 管怎么做、MCP 管怎么连"，但没讲透互补关系。把它们放进同一个任务看：
- **MCP** 提供**会执行的能力**（一个能真调数据库的 Tool）。它是"手"。
- **Skill** 提供**用这些能力的做法**（"分析报表时，先用 X 工具拉数、注意软删除字段、按这个模板输出"）。它是"菜谱/工作流"。
- 二者**正交、可叠加**：一个好的数据分析 Skill，正文里完全可以指挥 Agent 去调某个 MCP Server 的工具。**Skill 不替代 MCP，反而常常"编排"MCP 提供的工具。**

一句话记忆：**MCP 扩展 Agent"能做什么"，Skill 规范 Agent"该怎么做"。**

### 4.3 `description` 为什么是"生死字段"
课件反复强调 description 重要，但没点透机制：**只有 description 是启动时就注入模型上下文的**，Agent 全靠它在"广告层"决定要不要加载正文。所以一个 Skill "该触发却没触发"，99% 的病根在 description（缺触发词 / 太模糊 / 没写清适用边界），而**不在正文**。写 description 的实操要点：把最关键的使用场景放最前面、包含用户会说的原话、写清"不适用于……"、第三人称、别超 1024 字符。

### 4.4 让 LLM 做该做的、脚本做确定性的（职责分工）
课件"八个典型错误"里点了"别让 LLM 做确定性工作"，值得单独强调成方法论：**理解意图、提取参数、决定下一步、解释结果 → 交给 LLM；解析文件结构、格式转换、批量处理、精确计算、校验输出 → 交给 `scripts/` 里的脚本。** 这不仅更可靠，也省 token（脚本跑一次胜过 LLM 反复推理）。这是"确定性 vs 概率性"的边界划分，是工程化 Skill 的核心判断。

### 4.5 安全：SKILL.md 本身就是"指令"
容易被忽略的风险：`SKILL.md` 正文会被当作指令注入，第三方 Skill 可能夹带"把数据发到某地址""执行危险命令"等操作。企业环境**装第三方 Skill 前必须审**：① 正文与 description 是否一致；② 脚本有无危险操作；③ 有无数据外传逻辑；④ 权限声明是否最小化。再配合 `disable-model-invocation` 给高危 Skill 上锁。

---

## 五、Python 随堂补基础

本讲主体是 YAML/Markdown/Bash，Python 只零星出现在示例里。挑用到的语法点：

**1. YAML frontmatter 语法**（不是 Python，但天天写，先认清）
```yaml
---                 # 三横线开头
name: my-skill      # 键: 值
description: |      # 竖线 | 表示"下面是多行文本，保留换行"
  第一行
  第二行
---
```

**2. with 上下文管理器**（课件 PDF 示例：`with pdfplumber.open(...) as pdf:`）
```python
with open("file.txt") as f:   # 进入时打开文件
    data = f.read()
# 缩进块结束，文件自动关闭（哪怕中途报错也会关）
```

**3. try / except 异常处理**（课件脚本示例）
```python
try:
    with open(path) as f:
        return f.read()
except FileNotFoundError:          # 只捕获"文件不存在"这种错
    print(f"未找到 {path}，创建默认文件")
    open(path, "w").close()
    return ""
```

**4. f-string 格式化字符串**（脚本里到处是）
```python
name = "张三"
print(f"你好 {name}，今天几号")   # f"..." 里 {} 会被变量值替换
```

> 说明：本讲不像 MCP 那讲有大量异步代码，重点在"会读 YAML + 会看简单 Python/Bash 脚本"即可，深水区（async 等）见笔记 11。

---

## 六、自测清单

**是什么**
1. 一句话说清 Skill 是什么？为什么说它"像菜谱不像厨师"？
2. Skill 的目录里，哪个文件是必须的？`scripts/`、`references/`、`assets/` 各对应 Agent 的什么动作（跑/看/填）？
3. `SKILL.md` 由哪两部分组成？必填的两个 frontmatter 字段是什么？
4. 渐进式披露的三层分别在什么时机、加载什么内容？
5. `name` 的命名规则是什么（字符集、长度、风格）？

**为什么**
6. 为什么不能把所有指令一股脑塞进上下文？渐进式披露怎么解决这个问题？
7. 为什么 `description` 是"最重要的字段"？"该触发却没触发"通常病根在哪？
8. 为什么"用中文回复""你叫小助手"这类指令不适合做成 Skill？
9. 为什么高风险操作（部署、删数据）要收紧自由度、甚至加 `disable-model-invocation`？
10. 为什么"格式转换、精确计算"该交给脚本而不是 LLM？
11. 为什么第三方 Skill 装之前必须审？它和普通软件包的风险有何不同？

**什么时候用**
12. 什么样的任务适合做成 Skill（四个特征）？什么样的不适合？
13. 判断"写 Prompt 还是包成 Skill"的那句黄金问法是什么？
14. 正文什么时候该拆到 `references/`？什么时候该做 `assets/` 模板？
15. Skill 和 MCP 同时出现在一个任务里时，各自负责什么？举个例子。

---

## 七、动手小练习

**练习 A（约 25 分钟）：写一个"生成学习周报"的 Skill**（对标课件附录示例一）
1. 建目录 `weekly-report/`，内含 `SKILL.md` 和 `assets/template.md`。
2. `SKILL.md` 的 frontmatter 写好 `name`（小写连字符）、`description`（含触发词"周报/学习总结"+ 写清"不适用于月报"，第三人称，≤1024 字符）。
3. 正文写清执行步骤（算本周起止 → 逐项追问 → 读模板 → 填充 → 输出）和"信息少时主动追问、不编造"的边界。
4. 在 Claude Code 里把它放进 `.claude/skills/`，输入 `/skills` 确认被识别，再说"帮我写本周周报"验证能自动触发。
5. 自检：把 `description` 里的触发词删掉，观察是否还能触发——亲手体会 description 的"生死"作用。

**练习 B（约 20 分钟）：给一个 Skill 做"自由度分级"改造**
1. 拿课件的"数据库迁移"（低自由度）和"代码审查"（高自由度）两个例子做参照。
2. 自选一个任务（如"给生产库跑一条清理脚本"），先按"高自由度"随便写，再改写成"低自由度"版本：给精确命令、标注"不要修改命令/参数"、写清"失败立即停止并回传错误"。
3. 对比两版，用一句话总结：为什么这个任务必须收紧自由度。
4. 加一个"可判定的验证清单"（如 `[ ] 迁移前已备份`、`[ ] 迁移后行数一致`），体会"验证点"如何防止 Agent 假装完成。
