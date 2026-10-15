---
name: answer-in-final-message
description: 回答/讲解必须完整写在最后一条消息里；工具调用（改笔记）放前面做完，别只写进 md
metadata:
  node_type: memory
  type: feedback
  originSessionId: ff981577-db45-4261-b7f0-7b0e82dd7cef
  modified: 2026-09-30T02:45:23.752Z
---

2026-09-30 用户说"你不要只追加到 md 文档中，也需要在当前窗口输出"。原因：我把讲解写在工具调用之前，最后一条只剩"已追加到笔记"，用户在窗口里看不到答案。

**Why:** 用户只能可靠看到最后一条消息；工具调用之间的文字可能看不到。
**How to apply:** 先做完所有 Edit/Write（追加笔记、改记忆），最后一条消息再完整输出讲解正文 + 🔖要记，结尾一句提醒重开笔记。配合 [[module6-notes-doc]]。
