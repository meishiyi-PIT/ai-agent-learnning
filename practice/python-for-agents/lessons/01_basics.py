# -*- coding: utf-8 -*-
"""
Lesson 01 · 基础：f-string / dict / list / 环境变量 / 程序入口   （约 10 分钟）

对应你的课件代码：p1/prompt.PY —— 学完本课你就能完全读懂它。
运行方式：python lessons/01_basics.py
"""

import os

# ============================================================
# 1. f-string —— 你的课件里出现频率第一的语法
# ============================================================
# 在字符串前加 f，就能用 {} 直接嵌入变量或表达式。
# LLM 的 prompt 拼装全靠它。

name = "DeepSeek"
temperature = 0.73456

print(f"模型是 {name}")                     # 嵌入变量
print(f"温度是 {temperature:.2f}")          # :.2f 保留两位小数 -> 0.73
print(f"大写：{name.upper()}")              # {} 里可以写任何表达式

long_text = "Agent 是一种能自主调用工具完成任务的 AI 程序"
print(f"预览：{long_text[:10]}...")         # [:10] 是切片：取前 10 个字符
# 切片规则：s[start:end]，含 start 不含 end；省略即到头/到尾
print(f"最后4个字符：{long_text[-4:]}")     # 负数从末尾数

# ============================================================
# 2. list（列表）—— LLM 的对话历史就是一个 list
# ============================================================
messages = []                               # 空列表
messages.append({"role": "system", "content": "你是一个助手"})   # 追加元素
messages.append({"role": "user", "content": "你好"})

print(f"\n消息条数：{len(messages)}")        # len() 求长度
print(f"第一条：{messages[0]}")             # 下标从 0 开始
print(f"最后一条：{messages[-1]}")          # -1 表示最后一个

# 遍历列表：for 循环
for msg in messages:
    print(f"  [{msg['role']}] {msg['content']}")
    # 注意：外层用了双引号 f"..."，里层取 key 就用单引号 msg['role']

# ============================================================
# 3. dict（字典）—— API 请求/响应、工具参数，全是 dict
# ============================================================
config = {
    "model": "deepseek-chat",
    "temperature": 0.7,
    "max_tokens": 1024,
}

print(f"\n模型：{config['model']}")          # 用 key 取值；key 不存在会报错 KeyError

# ★ 重点：.get(key, 默认值) —— key 不存在时不报错，返回默认值
#   你的课件里大量出现，比如读取 LLM 返回的可选字段
timeout = config.get("timeout", 30)          # config 里没有 timeout -> 得到 30
print(f"超时：{timeout}")

config["stream"] = True                      # 新增/修改 key
print(f"所有 key：{list(config.keys())}")

# 遍历字典：.items() 同时拿到 key 和 value
for key, value in config.items():
    print(f"  {key} = {value}")

# ============================================================
# 4. 环境变量 —— API Key 的标准读法
# ============================================================
# 你的课件里的套路（p1/prompt.PY 开头就是）：
#   from dotenv import load_dotenv
#   load_dotenv()                          # 把 .env 文件的内容加载进环境变量
#   api_key = os.getenv("OPENAI_API_KEY")  # 读取；不存在返回 None

api_key = os.getenv("OPENAI_API_KEY", "未设置")   # 第二个参数是默认值
print(f"\nAPI Key：{api_key[:6]}..." if api_key != "未设置" else "\nAPI Key 未设置（正常，这只是演示）")

# ============================================================
# 5. if __name__ == "__main__" —— 程序入口约定
# ============================================================
# 每个 .py 文件都有一个内置变量 __name__：
#   - 直接运行这个文件时，__name__ == "__main__"，if 里的代码会执行
#   - 被别的文件 import 时，__name__ 是模块名，if 里的代码不执行
# 作用：让文件既能当脚本跑，又能被安全地 import。

def main():
    print("\n[main] 只有直接运行本文件时才会看到这行")

if __name__ == "__main__":
    main()

# ============================================================
# 练习（写完后直接运行本文件验证；参考答案在最底部）
# ============================================================
# 练习1：定义 user = {"name": "小明", "level": 3}，
#        用 f-string 打印：小明 当前等级是 3
# 练习2：用 .get() 从 user 中读取 "email"，默认值 "无邮箱"，打印出来
# 练习3：把 {"role": "assistant", "content": "收到"} 追加进 messages，
#        并打印最后一条消息的 content

# 在这里写你的答案：



# ------------------ 参考答案 ------------------
# user = {"name": "小明", "level": 3}
# print(f"{user['name']} 当前等级是 {user['level']}")
# print(user.get("email", "无邮箱"))
# messages.append({"role": "assistant", "content": "收到"})
# print(messages[-1]["content"])
