"""
课件 5《大模型推理部署》第二部分第 7 节：采样——最后一个 token 是怎么"被选中的"

运行（在 meishiyi/09_HuggingFace 目录下，用本项目 venv，CPU 即可）：
    .venv/Scripts/python -X utf8 inference_deploy/s1_sampling.py

这段代码回答两个问题：
1. 模型每一步吐出来的到底是什么？——不是一个字，而是词表上每个 token 的概率（Qwen3 词表 151,936 个）。
2. temperature / top_k / top_p / do_sample 各自动了这张概率表的哪一部分？

结构：
- 第一段：只做一次前向，把"下一个 token"的概率表打出来，看 temperature 怎么改变它（这是采样的本质）。
- 第二段：用 model.generate 把课件里的四个参数真正跑一遍，对比贪心 vs 采样的输出。

Python 语法点（Java 背景）：
- `**inputs`：把字典拆成关键字参数传进去，等于 generate(input_ids=..., attention_mask=...)。
- `torch.no_grad()`：推理不需要反向传播，关掉梯度记录省内存、提速。
- `logits[0, -1]`：取 batch 里第 0 条、序列最后一个位置的分数向量（形状 [词表大小]）。
"""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_DIR = "models/Qwen3-0.6B"   # 本地目录，已从 ModelScope 下好；换成 "Qwen/Qwen3-0.6B" 就是课件写法

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
# CPU 上 bfloat16 很慢，直接用 float32（0.6B × 4 字节 ≈ 2.4 GB 内存，本机够）
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.float32)
model.eval()

# Qwen3 是对话模型：套对话模板并关掉思考模式，否则它会先输出一大段 <think>
messages = [{"role": "user", "content": "用一句话解释什么是递归。"}]
text = tokenizer.apply_chat_template(
    messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
)
inputs = tokenizer(text, return_tensors="pt")
print(f"输入 token 数: {inputs['input_ids'].shape[1]}")

# ============ 第一段：看一眼"下一个 token 的概率表" ============
# 回答的第一个字几乎必然是"递"（概率 1.00），看不出温度的作用；
# 所以把探针放在"递归是一种通过"之后——这里"函数 / 定义 / 重复 / 调用"都有可能，分布才有形状。
probe = tokenizer(text + "递归是一种通过", return_tensors="pt")
with torch.no_grad():
    out = model(**probe)                  # 这一次前向就是 Prefill
logits = out.logits[0, -1]                # 最后一个位置的分数，形状 [151936]
print(f"logits 形状: {tuple(logits.shape)}  <- 词表上每个 token 一个分数")


def show_topk(t: float, k: int = 5):
    """temperature 的数学定义：logits / T 再 softmax。T<1 分布变尖，T>1 分布变平。"""
    probs = torch.softmax(logits / t, dim=-1)
    top = torch.topk(probs, k)
    items = [f"{tokenizer.decode([i]).strip()!r}:{p:.2f}" for p, i in zip(top.values, top.indices)]
    print(f"T={t:<4} 前{k}个候选及概率: " + "  ".join(items))


print('前缀 "递归是一种通过" 之后，下一个 token 的候选：')
for t in (0.3, 0.7, 1.0, 1.5):
    show_topk(t)

# 贪心 = 永远取概率最大的那个
print("贪心会选:", repr(tokenizer.decode([int(torch.argmax(logits))])))

# ============ 第二段：课件的四个参数真跑一遍 ============
def gen(**kw):
    with torch.no_grad():
        ids = model.generate(**inputs, max_new_tokens=40, pad_token_id=tokenizer.eos_token_id, **kw)
    return tokenizer.decode(ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()


print("\n[贪心 do_sample=False] 跑两次，应该一模一样：")
print(" 1:", gen(do_sample=False))
print(" 2:", gen(do_sample=False))

print("\n[采样 T=0.7 top_k=50 top_p=0.9] 跑两次，通常不一样：")
torch.manual_seed(1); print(" 1:", gen(do_sample=True, temperature=0.7, top_k=50, top_p=0.9))
torch.manual_seed(2); print(" 2:", gen(do_sample=True, temperature=0.7, top_k=50, top_p=0.9))

print("\n[采样 T=1.5] 温度拉高，更容易跑偏：")
torch.manual_seed(3); print(" 1:", gen(do_sample=True, temperature=1.5, top_k=50, top_p=0.95))
