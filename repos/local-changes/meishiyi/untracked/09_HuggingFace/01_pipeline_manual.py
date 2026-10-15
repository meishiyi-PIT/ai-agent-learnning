"""课件 2.5 —— 把 Pipeline 扒光：不用 pipeline()，手动走一遍"预处理 → 模型推理 → 后处理"三站。

【挖空版】所有 ____ 都要你自己填；填之前先把文件末尾的 4 道预测题答案写在注释里，
跑完再对照真实输出改。跑法：
    PYTHONUTF8=1 uv run python 01_pipeline_manual.py

【这节课的三问】（跑完后回来填）
  ① 解决什么问题：
  ② 核心 API/模式：
  ③ 对应工作区哪个项目的哪个文件：
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# 课件写的是 Hub id "uer/roberta-base-finetuned-dianping-chinese"；这里改成本地目录（课件 1.4/1.6 的做法），
# 原因见 README"本机环境与课件的差异"表：这个仓库只有老格式 .bin 权重，用 Hub id 加载时
# transformers 会在后台线程偷偷下 400MB 的 safetensors，脚本打印完了进程也要等它几分钟才退出。
# 本地目录里已经是 safetensors，加载零网络请求。from_pretrained 认"Hub id"也认"本地目录"，其余代码一字不改。
model_id = "./models/roberta-base-finetuned-dianping-chinese"

# 【Python 补课 · 为什么 tokenizer 和 model 都用 from_pretrained 而不是 new】
# Java 里对象靠构造器 new 出来；这里的 from_pretrained 是"类方法工厂"（@classmethod）：
# 读磁盘上的 config.json 决定该造哪个具体子类、再把权重文件灌进去，最后把造好的对象返回给你。
# 所以它是"按配置文件造对象"，不是简单的构造器——这也是为什么模型和分词器必须"原配"：
# 两者读的是同一个仓库里的配置。
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForSequenceClassification.from_pretrained(model_id)

text = "这家外卖送得飞快，汤一滴没洒！"

# ===== 第一站：预处理（文本 → 张量）=====
# 直接"调用"tokenizer 对象（相当于 Java 里对象实现了一个 call() 方法，Python 叫 __call__），
# 传 return_tensors="pt" 让它返回 PyTorch 张量而不是普通 list（pt = PyTorch）。
inputs = tokenizer(text, return_tensors=____)

# 探针：亲眼看看第一站产出了什么——这是后面 **inputs 能成立的根据
print("inputs 的类型：", type(inputs).__name__)
print("inputs 的键：", list(inputs.keys()))
print("input_ids 形状：", inputs["input_ids"].shape)
# convert_ids_to_tokens：把一串 id 翻回 token，看看句子被切成了什么、头尾多了什么
print("tokens：", tokenizer.convert_ids_to_tokens(inputs["input_ids"][0]))

# ===== 第二站：模型推理（张量 → 每个类别一个原始分数）=====
# 【Python 补课 · ** 是什么】
# inputs 是一个"键→值"的字典，形如 {"input_ids": 张量, "token_type_ids": 张量, "attention_mask": 张量}。
# model(**inputs) 等价于手写 model(input_ids=张量, token_type_ids=张量, attention_mask=张量)：
# 两个星号把字典"拆开"成一个个关键字参数。Java 没有对应语法，最接近的是"把 Map 里每个
# entry 按 key 名对号入座传给方法"。（单星号 *list 是拆列表成位置参数，和它是一对。）
#
# 【Python 补课 · with torch.no_grad()】
# with 块 = Java 的 try-with-resources：进入时关掉"记录梯度"的开关，退出时自动恢复。
# 推理不需要反向传播，不记梯度能省一半内存、跑得更快。训练时才需要梯度。
with torch.no_grad():
    outputs = model(____)
logits = outputs.____   # 原始分数，未归一化；形状 [样本数, 类别数]

print("outputs 的类型：", type(outputs).__name__)
print("logits 形状：", logits.shape)
print("logits：", logits)

# ===== 第三站：后处理（原始分数 → 人类可读的标签）=====
# 【数学补课 · softmax，手算一遍】
# 作用：把任意一组实数变成"加起来等于 1、每个都在 0~1 之间"的概率。
# 步骤：每个数先取 e 的幂（保证为正、且拉大差距），再各自除以总和。
# 算例：logits = [-1.2, 2.8]
#   e^-1.2 = 0.30，e^2.8 = 16.44，总和 = 16.74
#   probs = [0.30/16.74, 16.44/16.74] = [0.018, 0.982]   ← 加起来 = 1
# dim=-1 表示"沿最后一个维度做"，对 [1, 2] 形状的张量就是对每一行的 2 个类别分数做。
probs = torch.softmax(logits, dim=____)
print("probs：", probs, "  概率之和：", probs.sum().item())

# argmax：返回最大值所在的下标（不是最大值本身）。[0.018, 0.982] → 下标 1
# .item()：把只含一个数的张量取成普通 Python 数字（int），后面才能拿它当字典的 key
pred_id = torch.argmax(probs, dim=-1).____()

# id2label：模型 config 里存的"下标 → 标签名"字典，00_check_env.py 已经打印过它的内容
label = model.config.____[pred_id]

# 【Python 补课 · f-string】f"{变量:.4f}" = 保留 4 位小数；probs[0][pred_id] 是"第 0 个样本、第 pred_id 类"的概率
print(f"预测标签：{label}，置信度：{probs[0][pred_id]:.4f}")


# ============================================================
# 预测题（跑之前把答案写在每题下面；跑完对照输出，错了写下"错在哪"）
# ------------------------------------------------------------
# Q1. inputs 的键有哪几个？（提示：课件 3.4 的"三件套"）
#     我的预测：
# Q2. input_ids 的形状是 [1, N]，N 是多少？（提示：课件 3.2 说中文按字切、encode 会加特殊 token；
#     数一数句子里的字符，别忘了标点）
#     我的预测：
# Q3. logits 的形状是什么？为什么第二个数是 2 而不是 5（明明是"1~5 星"评论）？
#     我的预测：
# Q4. probs 两个数之和是多少？pred_id 会是 0 还是 1？
#     我的预测：
# ============================================================


# ============================================================
# 加练（跑通上面之后做，深度②"能改参数"）
# ------------------------------------------------------------
# A. 把 text 换成差评 "配送慢不说，汤还洒了一半，emo 了。"，先预测 pred_id，再跑。
# B. 一次喂两句：tokenizer([句子1, 句子2], return_tensors="pt", padding=True)
#    先预测 input_ids 的形状和 attention_mask 里 0 出现的位置，再跑；
#    这一步做完，课件 3.4 的 attention_mask 就不用背了。
# C. 用课件 2.3 方式三：pipeline("text-classification", model=model, tokenizer=tokenizer)
#    对同样两句话跑一次，比较它给的 score 和你手算的 probs 是否一致——一致，说明
#    "pipeline 就是这三站"你已经亲手验证过了。
# ============================================================
