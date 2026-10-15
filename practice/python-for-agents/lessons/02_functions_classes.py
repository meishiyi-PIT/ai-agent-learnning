# -*- coding: utf-8 -*-
"""
Lesson 02 · 函数、类、异常、**kwargs   （约 10 分钟）

对应你的课件代码：Multi-Agent/agent.py、Multi-Agent/tools.py
—— 那是一个不依赖框架、手写的 Agent 工具循环，学完本课就能读懂它。
运行方式：python lessons/02_functions_classes.py
"""

import json

# ============================================================
# 1. 函数 + 类型注解 —— 课件里的函数几乎都长这样
# ============================================================
# def 函数名(参数: 类型 = 默认值) -> 返回类型:
# 注解只是"说明书"，Python 不强制检查，但框架（如 MCP）会用它自动生成工具 schema。

def search(query: str, top_k: int = 3) -> str:
    """模拟搜索工具。docstring 写在这里，LangChain 的 @tool 会把它作为工具描述给 LLM 看。"""
    return f"关于「{query}」的前 {top_k} 条结果"

print(search("LangGraph"))                 # top_k 用默认值 3
print(search("RAG", top_k=5))              # 关键字参数：指名道姓地传，可读性好
print(search.__doc__)                      # docstring 可以被程序读取——这就是 @tool 的原理

# ============================================================
# 2. **kwargs 与字典解包 —— Multi-Agent/agent.py 的核心技巧
# ============================================================
# **kwargs：函数定义处，把多余的关键字参数收进一个 dict
# **dict  ：函数调用处，把 dict 展开成关键字参数（方向相反！）

def call_llm(model: str, **kwargs) -> None:
    # kwargs 是一个 dict，收集了 model 之外的所有关键字参数
    print(f"调用 {model}，额外参数: {kwargs}")

call_llm("deepseek-chat", temperature=0.7, max_tokens=100)

# 反向：先把参数组装成 dict，再一次性展开传入
# 你课件里的真实写法：self.client.chat.completions.create(**kwargs)
params = {"model": "deepseek-chat", "temperature": 0.2}
call_llm(**params)      # 等价于 call_llm(model="deepseek-chat", temperature=0.2)

# ============================================================
# 3. try / except —— 工具调用失败不能让整个 Agent 崩溃
# ============================================================
# 你课件里的高频场景：解析 LLM 返回的 JSON（LLM 可能输出格式错误的内容）

bad_json = '{"tool": "search", "args": '   # 故意残缺的 JSON

try:
    data = json.loads(bad_json)            # 可能抛异常的代码放 try 里
except json.JSONDecodeError as e:          # as e：把异常对象存进变量 e
    print(f"JSON 解析失败：{e}")
    data = {}                              # 出错时给个兜底值，程序继续跑

# 更通用的写法（课件里最常见）：
try:
    result = 10 / 0
except Exception as e:                     # Exception 能接住几乎所有错误
    print(f"工具执行出错：{type(e).__name__}: {e}")
finally:
    print("finally 无论成败都会执行（常用来清理资源）")

# ============================================================
# 4. 类 class —— Agent、Tool、Client 都是类
# ============================================================
# 三个要点：__init__ 是构造函数；self 代表实例自己；方法第一个参数必须是 self。

class MiniAgent:
    # 类属性：所有实例共享（课件里工具类常用 name = "milvus_search" 这种写法）
    name = "mini-agent"

    def __init__(self, model: str, temperature: float = 0.7):
        # 实例属性：每个实例自己的数据，必须挂在 self 上
        self.model = model
        self.temperature = temperature
        self.history: list[dict] = []      # 对话历史；list[dict] 是泛型注解

    def add_message(self, role: str, content: str) -> None:
        """往历史里追加一条消息。"""
        self.history.append({"role": role, "content": content})

    def chat(self, user_input: str) -> str:
        """模拟一轮对话（真实版这里会调 LLM API）。"""
        self.add_message("user", user_input)          # 方法内部用 self.xxx 调用自己的方法
        reply = f"[{self.model}] 已收到 {len(self.history)} 条消息"
        self.add_message("assistant", reply)
        return reply

# 实例化：不需要传 self，Python 自动传
agent = MiniAgent("deepseek-chat")
print(f"\n{agent.chat('你好')}")
print(agent.chat("介绍一下 LangGraph"))
print(f"历史共 {len(agent.history)} 条")

# ============================================================
# 5. with 语句 —— 自动关闭资源
# ============================================================
# 打开文件、线程池、临时文件都用 with：离开代码块时自动清理，忘了 close 也不怕。
# 课件真实用例：Multi-Agent/tools.py 的 tempfile、Agentic_Rag 的 ThreadPoolExecutor

import tempfile, os

with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
    f.write("hello agent")
    temp_path = f.name
# 离开 with 块后文件已自动关闭
with open(temp_path, encoding="utf-8") as f:
    print(f"\n读回临时文件：{f.read()}")
os.unlink(temp_path)                       # 删除临时文件

# ============================================================
# 练习
# ============================================================
# 练习1：写函数 calc_bmi(weight: float, height: float) -> str，
#        返回 f"BMI = {bmi:.1f}"（bmi = weight / height ** 2），并调用打印
# 练习2：给 MiniAgent 加一个 clear() 方法清空 history，调用后打印历史长度
# 练习3：用 try/except 解析 '{"a": 1}'，成功则打印 data["a"]

# 在这里写你的答案：



# ------------------ 参考答案 ------------------
# def calc_bmi(weight: float, height: float) -> str:
#     bmi = weight / height ** 2
#     return f"BMI = {bmi:.1f}"
# print(calc_bmi(65, 1.75))
#
# # 练习2：在类里加（注意缩进到 class 内部）：
# #     def clear(self) -> None:
# #         self.history = []
# # agent.clear(); print(len(agent.history))
#
# try:
#     data = json.loads('{"a": 1}')
#     print(data["a"])
# except json.JSONDecodeError as e:
#     print(f"解析失败: {e}")
