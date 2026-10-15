---
name: user-python-level
description: 用户 Python 基础较弱，讲课时需随堂补充 Python 知识点，掌握后改为只讲难点
metadata: 
  node_type: memory
  type: user
  originSessionId: c83a3a80-bcbf-4ea4-9b4a-6349a26b3761
  modified: 2026-07-25T06:51:30.499Z
---

用户自述 Python 基础比较弱（2026-07-25），但实测比自述的要好：学 Multi-Agent 课件时，`os.getenv`/`load_dotenv`/环境变量这类基础点被用户明确说"太基础了"，主动跳到课件更后面的小节（3.4）。

**结论：不要在环境变量、基本语法这类入门知识点上停留提问**，默认用户能看懂。随堂只补语法上确实有难度的点（装饰器 `@tool`、类型注解怎么被框架读取、生成器 `stream()`、TypedDict、asyncio、闭包等），且优先讲"这段代码在做什么/为什么这样设计"而不是掰开揉碎讲 Python 入门语法。如果后续发现某个稍难的点用户也秒懂，可以进一步收窄补充范围；反之如果基础点卡住了再放宽。

相关：[[learning-requirements]]
