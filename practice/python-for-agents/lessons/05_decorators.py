# -*- coding: utf-8 -*-
"""
Lesson 05 · 装饰器：@tool 到底干了什么   （约 8 分钟）

对应你的课件代码：
  - ai-example/08_multi_agent/supervisor_demo.py 的 @tool
  - ai-example/06_mcp/my_mcp_server.py 的 @mcp.tool()
  - MemoryAgents backend 的 @app.get / @app.post（FastAPI）
运行方式：python lessons/05_decorators.py
"""

# ============================================================
# 1. 核心认知：函数也是对象，可以当参数传、当返回值还
# ============================================================
def shout(text: str) -> str:
    return text.upper() + "!"

f = shout                  # 函数名不加括号 = 函数本身（对象）；加括号才是调用
print(f("hello"))          # HELLO!  —— f 和 shout 是同一个函数

# ============================================================
# 2. 装饰器 = "接收一个函数、返回一个新函数"的函数
# ============================================================
# @xxx 只是语法糖：
#     @log_calls              等价于        def add(...): ...
#     def add(...): ...                     add = log_calls(add)

def log_calls(func):
    """一个最简单的装饰器：调用前后打印日志。"""
    def wrapper(*args, **kwargs):          # *args/**kwargs：原样接收任何参数
        print(f"  >> 调用 {func.__name__}，参数 {args} {kwargs}")
        result = func(*args, **kwargs)     # 执行原函数
        print(f"  << 返回 {result}")
        return result
    return wrapper                         # 返回包装后的新函数

@log_calls
def add(a: int, b: int) -> int:
    return a + b

print("带日志的 add:")
add(3, 5)                                  # 自动打印调用日志——原函数一行没改

# ============================================================
# 3. 实战：自己写一个 @register_tool —— 揭开 LangChain @tool 的魔法
# ============================================================
# LangChain 的 @tool、MCP 的 @mcp.tool() 本质都是：
#   把函数登记到一个"工具注册表"里，并利用 函数名/注解/docstring 生成工具描述给 LLM。

TOOLS: dict[str, dict] = {}                # 工具注册表：名字 -> 工具信息

def register_tool(func):
    """模仿 @tool：把函数登记进 TOOLS，函数本身原样返回。"""
    TOOLS[func.__name__] = {
        "func": func,
        "description": func.__doc__,       # ★ docstring 就是给 LLM 看的工具说明
        "params": func.__annotations__,    # ★ 类型注解自动变成参数 schema
    }
    return func

@register_tool
def calculator(expression: str) -> float:
    """计算数学表达式，例如 '3 * (2 + 5)'。"""
    return eval(expression)                # 演示用；生产代码要用安全的表达式求值

@register_tool
def get_weather(city: str) -> str:
    """查询指定城市的天气。"""
    return f"{city}：晴，26°C"

print(f"\n注册表里有 {len(TOOLS)} 个工具:")
for name, info in TOOLS.items():
    print(f"  - {name}: {info['description']}  参数: {info['params']}")

# Agent 的工具调用环节就是：按名字查表 -> 拿函数 -> 传参执行
tool_name, tool_args = "calculator", {"expression": "3 * (2 + 5)"}
result = TOOLS[tool_name]["func"](**tool_args)     # **解包：dict 展开成关键字参数
print(f"执行 {tool_name} -> {result}")

# ============================================================
# 4. 带参数的装饰器 —— 认识 @mcp.tool() 为什么有括号
# ============================================================
# @log_calls     不带括号：log_calls 本身就是装饰器
# @mcp.tool()    带括号：  mcp.tool() 被调用后【返回】一个装饰器（多包了一层）
# @app.get("/chat")  同理：先传入路径参数，返回真正的装饰器

def tool_with_name(name: str):             # 第一层：接收装饰器参数
    def decorator(func):                   # 第二层：真正的装饰器
        TOOLS[name] = {"func": func, "description": func.__doc__, "params": func.__annotations__}
        return func
    return decorator

@tool_with_name("web_search")              # 有括号！先调用 tool_with_name 拿到装饰器
def search_impl(query: str) -> str:
    """联网搜索。"""
    return f"搜索「{query}」的结果..."

print(f"\n自定义名字注册: {'web_search' in TOOLS}")

# ============================================================
# 读课件时认识这些装饰器就够了（原理都同上）：
# ------------------------------------------------------------
# @tool               LangChain：函数 -> LLM 可调用的工具
# @mcp.tool()         MCP：注册工具（注解自动生成 schema）
# @app.get("/x")      FastAPI：函数 -> HTTP 接口
# @dataclass          自动生成 __init__ 等（见 Lesson 03）
# @property           方法伪装成属性，obj.x 不用加括号
# @abstractmethod     抽象方法：子类必须实现（适配器模式用）
# ============================================================

# ============================================================
# 练习
# ============================================================
# 练习1：用 @register_tool 注册一个 translate(text: str) -> str 工具
#        （docstring 写"把文本翻译成英文"，返回值随意），打印 TOOLS 里它的 description
# 练习2：写一个装饰器 @twice，让被装饰的函数执行两次并返回最后一次结果，
#        用它装饰一个打印 "hi" 的函数验证

# 在这里写你的答案：



# ------------------ 参考答案 ------------------
# @register_tool
# def translate(text: str) -> str:
#     """把文本翻译成英文。"""
#     return f"EN({text})"
# print(TOOLS["translate"]["description"])
#
# def twice(func):
#     def wrapper(*args, **kwargs):
#         func(*args, **kwargs)
#         return func(*args, **kwargs)
#     return wrapper
#
# @twice
# def say_hi():
#     print("hi")
# say_hi()
