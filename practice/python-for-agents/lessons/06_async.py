# -*- coding: utf-8 -*-
"""
Lesson 06 · async / await 异步   （约 7 分钟）

对应你的课件代码：a2a/server.py（AsyncOpenAI）、ai-example/MemoryAgents/backend（FastAPI 全异步）
注意：你的其他项目（Agentic_Rag、Multi-Agent 等）基本是同步代码——
     异步只在这两个项目集中出现，读到它们时再回来复习本课即可。
运行方式：python lessons/06_async.py
"""

import asyncio
import time

# ============================================================
# 1. 为什么需要异步？
# ============================================================
# 调 LLM API 一次要等好几秒，等待期间 CPU 什么都不干。
# 异步 = 在"等网络"的时候切出去干别的活。多个 LLM 调用可以同时等，总耗时 ≈ 最慢的那个。

# ============================================================
# 2. 三个关键字/函数（读懂 90% 异步代码就靠它们）
# ------------------------------------------------------------
# async def f():   定义"协程函数"——调用它不会执行，只得到一个协程对象
# await xxx        真正执行并等待结果；只能写在 async def 里面
# asyncio.run(f()) 同步世界的入口：启动事件循环，跑一个协程
# ============================================================

async def call_llm(name: str, seconds: float) -> str:
    """模拟一次 LLM API 调用（asyncio.sleep 模拟网络等待）。

    对照课件 a2a/server.py 的真实代码：
        async def invoke(self, user_request: str) -> str:
            response = await self.client.chat.completions.create(...)
            return response.choices[0].message.content
    """
    print(f"  [{name}] 发出请求...")
    await asyncio.sleep(seconds)           # 模拟等待网络；真实代码这里是 await client.xxx
    print(f"  [{name}] 收到响应")
    return f"{name} 的回答"

async def serial_demo() -> None:
    """串行：一个等完再等下一个。"""
    start = time.perf_counter()
    a = await call_llm("路由Agent", 1.0)
    b = await call_llm("检索Agent", 1.0)
    print(f"串行总耗时: {time.perf_counter() - start:.1f}s（1.0 + 1.0）\n")

async def concurrent_demo() -> None:
    """并发：asyncio.gather 同时发出，一起等。"""
    start = time.perf_counter()
    a, b = await asyncio.gather(           # ★ gather：并发跑多个协程，按顺序返回结果
        call_llm("路由Agent", 1.0),
        call_llm("检索Agent", 1.0),
    )
    print(f"并发总耗时: {time.perf_counter() - start:.1f}s（≈ 最慢的那个）")
    print(f"结果: {a} | {b}\n")

async def main() -> None:
    print("=== 串行 ===")
    await serial_demo()
    print("=== 并发 ===")
    await concurrent_demo()

    # ============================================================
    # 3. 常见坑：忘了 await
    # ============================================================
    coro = call_llm("测试", 0.1)           # 没有 await：只是拿到协程对象，函数根本没执行！
    print(f"忘了 await 得到的是: {type(coro).__name__}（函数没执行）")
    await coro                             # 补上 await 才真正执行

if __name__ == "__main__":
    asyncio.run(main())                    # ★ 整个程序的异步入口，只在最外层调用一次

# ============================================================
# 读课件时的三条经验：
# ------------------------------------------------------------
# 1. 看到 async def，里面的 await 行 = "这里在等 I/O，可能切走干别的"
# 2. FastAPI 路由函数（@app.post 装饰的 async def）由框架负责调度，
#    你永远不用自己写 asyncio.run —— 它藏在 uvicorn 里
# 3. 同步函数里不能用 await；异步函数里调同步的耗时函数会卡住整个循环
#    （课件 MemoryAgents 用 async 的库如 AsyncOpenAI 就是为了避开这条）
# ============================================================

# ============================================================
# 练习
# ============================================================
# 练习1：写 async def fetch_doc(doc_id: int) -> str，睡 0.5 秒后返回 f"文档{doc_id}"，
#        用 asyncio.gather 并发获取文档 1、2、3 并打印结果
# （提示：写一个新的 async def practice() 函数，把 asyncio.run(main()) 换成
#   asyncio.run(practice()) 来运行你的练习）

# ------------------ 参考答案 ------------------
# async def fetch_doc(doc_id: int) -> str:
#     await asyncio.sleep(0.5)
#     return f"文档{doc_id}"
#
# async def practice():
#     docs = await asyncio.gather(fetch_doc(1), fetch_doc(2), fetch_doc(3))
#     print(docs)
#
# asyncio.run(practice())
