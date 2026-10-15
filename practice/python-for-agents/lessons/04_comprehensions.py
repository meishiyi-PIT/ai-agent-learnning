# -*- coding: utf-8 -*-
"""
Lesson 04 · 列表推导式 + enumerate + zip   （约 8 分钟）

对应你的课件代码：Agentic_Rag/app/graph.py（推导式密度最高的文件）
运行方式：python lessons/04_comprehensions.py
"""

# ============================================================
# 1. 基本形态：[表达式 for 元素 in 可迭代对象]
# ============================================================
# 推导式 = "for 循环 + append" 的一行写法，Agent 代码里处理数据的主力。

docs = ["  文档A  ", "文档B", "  文档C"]

# 传统写法：
cleaned = []
for d in docs:
    cleaned.append(d.strip())

# 推导式写法（完全等价，课件里全用这种）：
cleaned = [d.strip() for d in docs]
print(f"清洗后: {cleaned}")

# ============================================================
# 2. 带 if 过滤：[表达式 for 元素 in ... if 条件]
# ============================================================
results = [
    {"tool": "milvus_search", "status": "ok",    "score": 0.92},
    {"tool": "web_search",    "status": "error", "score": 0.0},
    {"tool": "sql_query",     "status": "ok",    "score": 0.85},
]

# 课件真实模式（Agentic_Rag/app/graph.py）：从结果中挑出所有出错的工具
errors = [r["tool"] for r in results if r["status"] == "error"]
print(f"出错的工具: {errors}")

# 挑出高分结果、只保留需要的字段（推导式里可以构造新 dict）
good = [{"tool": r["tool"], "score": r["score"]} for r in results if r["score"] > 0.8]
print(f"高分结果: {good}")

# ============================================================
# 3. 双重 for 展平嵌套列表 —— 课件里的高频写法
# ============================================================
# 多个检索工具各返回一批证据（列表的列表），要合并成一个平列表。
# 读法口诀：从左往右就是嵌套 for 循环的顺序。

batches = [["证据1", "证据2"], ["证据3"], ["证据4", "证据5"]]

# 等价的传统写法:                 推导式写法:
# flat = []
# for batch in batches:
#     for item in batch:
#         flat.append(item)
flat = [item for batch in batches for item in batch]
print(f"展平: {flat}")

# ============================================================
# 4. enumerate —— 遍历时同时拿到序号
# ============================================================
# enumerate(列表, start) 的 start 指定序号从几开始（默认 0）
# 课件真实用例：给检索到的文档编号后拼进 prompt

context = "\n".join(f"[{i}] {doc}" for i, doc in enumerate(flat, 1))
print(f"\n拼装的上下文:\n{context}")
# 说明：join 括号里没有方括号也能跑（生成器表达式），效果一样，不必深究区别。

# ============================================================
# 5. zip —— 两个列表配对遍历
# ============================================================
# 课件真实用例（Agentic_Rag/app/graph.py）：计划的步骤和执行结果一一配对
# strict=True：两个列表长度不一致就报错（避免静默丢数据），课件用的就是它

steps = ["检索", "评分", "回答"]
outcomes = ["ok", "ok", "done"]

for step, outcome in zip(steps, outcomes, strict=True):
    print(f"步骤[{step}] -> {outcome}")

# 配合推导式：
report = [{"step": s, "outcome": o} for s, o in zip(steps, outcomes, strict=True)]
print(f"执行报告: {report}")

# ============================================================
# 6. 实战组合拳 —— 模拟课件里一段真实的数据加工流程
# ============================================================
tool_results = [
    {"tool": "milvus", "evidence": ["向量库结果1", "向量库结果2"], "status": "ok"},
    {"tool": "web",    "evidence": [],                             "status": "error"},
    {"tool": "sql",    "evidence": ["数据库结果1"],                "status": "ok"},
]

evidence = [e for r in tool_results if r["status"] == "ok" for e in r["evidence"]]
failed  = [r["tool"] for r in tool_results if r["status"] == "error"]
summary = f"共 {len(evidence)} 条证据，失败工具：{failed or '无'}"
# `failed or '无'`：空列表是"假值"，所以 failed 为空时显示 '无' —— 课件常见小技巧
print(f"\n{summary}")
print("证据清单:", evidence)

# ============================================================
# 练习
# ============================================================
# 练习1：nums = [1, 2, 3, 4, 5, 6]，用推导式取出所有偶数的平方 -> [4, 16, 36]
# 练习2：用 enumerate 把 ["苹果", "香蕉"] 打印成 "1. 苹果" "2. 香蕉"
# 练习3：把 [["a", "b"], ["c"]] 展平成 ["a", "b", "c"]

# 在这里写你的答案：



# ------------------ 参考答案 ------------------
# nums = [1, 2, 3, 4, 5, 6]
# print([n ** 2 for n in nums if n % 2 == 0])
#
# for i, fruit in enumerate(["苹果", "香蕉"], 1):
#     print(f"{i}. {fruit}")
#
# print([x for sub in [["a", "b"], ["c"]] for x in sub])
