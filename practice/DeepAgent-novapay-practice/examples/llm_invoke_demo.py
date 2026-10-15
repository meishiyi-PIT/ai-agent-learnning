"""最小可跑示例:怎么直接调用裸模型 llm.invoke(...)。

运行方式(在项目根目录):
    uv run python examples/llm_invoke_demo.py

⚠️ 这会真的调用 .env 里配置的 DeepSeek 接口、消耗你的 API 额度。

——————————————————————————————————————————————————————————————
【核心认知:agent.invoke 和 llm.invoke 是两个不同的东西】
  · agent = create_deep_agent(...) 的返回值,是一张【编译好的 LangGraph 图】,
    它的 .invoke 要喂【图的状态字典】:  agent.invoke({"messages": [ {...} ]})
  · llm   = build_chat_model(...) 的返回值,是一个【裸 ChatOpenAI 模型】,
    它的 .invoke 直接喂【消息本身】:    llm.invoke("你要说的话")
  同名方法 .invoke,吃的输入不一样,因为它俩根本不是同一类对象。
  下次卡住先 type(x) 看清对象是什么类,再查那个类怎么调,别拿 A 的参数套 B。
——————————————————————————————————————————————————————————————
"""

from __future__ import annotations

from vendor_guard.agent import build_chat_model
from vendor_guard.settings import Settings


def main() -> None:
    # Settings.from_env() 读 .env 里的 DEEPSEEK_API_KEY / 模型名 / base_url,
    # build_chat_model 用这些配置造出一个 ChatOpenAI 实例(就是我们说的 llm)。
    llm = build_chat_model(Settings.from_env())

    # 先确认它到底是什么类——这一步就是“下次自己查”的第一招。
    print("llm 的类型:", type(llm).__name__)  # 期望打印 ChatOpenAI

    # —— llm.invoke 的 4 种合法输入,任选其一 ——

    # ① 最简单:直接给一个字符串
    resp = llm.invoke("用一句话解释什么是供应商准入尽调")

    # ② 消息元组列表:("角色", "内容")。system 定角色,human 是用户输入
    # resp = llm.invoke([("system", "你是风控助手"), ("human", "什么是制裁名单?")])

    # ③ 消息对象列表(更显式,需要 import):
    # from langchain_core.messages import SystemMessage, HumanMessage
    # resp = llm.invoke([SystemMessage("你是风控助手"), HumanMessage("什么是制裁名单?")])

    # ④ dict 列表:和 agent.invoke({"messages": [...]}) 里那种元素同款
    # resp = llm.invoke([{"role": "user", "content": "什么是制裁名单?"}])

    # 返回值是一个 AIMessage 对象;模型回的文字在 .content 里,不是直接 print(resp)。
    print("模型回复:", resp.content)


if __name__ == "__main__":
    main()
