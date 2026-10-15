"""课件 7《图解 MoE 结构》：路由怎么选专家 + 总参数 vs 激活参数。

1. 用 transformers 里 Qwen3-MoE 真正的 MoE 层（Qwen3MoeSparseMoeBlock），缩小成 4 个专家、每个 token 选 2 个，
   喂 5 个 token，看路由给每个 token 打的概率、选了谁、最后的权重
2. 按 Qwen3-30B-A3B 的公开配置在 meta 设备上搭空壳，数总参数和"每个 token 实际用到"的参数

运行：cd meishiyi/09_HuggingFace && .venv/Scripts/python -X utf8 arch_train/s14_moe_router.py
"""
import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, Qwen3MoeConfig
from transformers.models.qwen3_moe.modeling_qwen3_moe import Qwen3MoeSparseMoeBlock

# ---------- 1. 路由三步：x·W → softmax → 取 top-k ----------
torch.manual_seed(0)
small = Qwen3MoeConfig(hidden_size=8, moe_intermediate_size=16, num_experts=4, num_experts_per_tok=2, norm_topk_prob=True)
moe = Qwen3MoeSparseMoeBlock(small)
x = torch.randn(1, 5, 8)                                        # 5 个 token，每个是 8 维向量（随机数，代替真实 hidden）

logits = moe.gate(x.view(-1, 8))                                # 路由 = 一个 Linear：8 维 → 4 个专家各一个分
probs = F.softmax(logits, dim=-1)
top_p, top_i = torch.topk(probs, 2, dim=-1)
weights = top_p / top_p.sum(-1, keepdim=True)                   # norm_topk_prob：选中的两个重新归一到和为 1
print(f"路由层 gate 的形状 {tuple(moe.gate.weight.shape)} = [专家数, hidden]，就是一个没有偏置的 Linear")
for t in range(5):
    p = " ".join(f"{v:.2f}" for v in probs[t].tolist())
    print(f"  token{t}: 4 个专家的概率 [{p}] → 选专家 {top_i[t].tolist()}，权重 {[round(w, 2) for w in weights[t].tolist()]}")

with torch.no_grad():
    y = moe(x)
    y = y[0] if isinstance(y, tuple) else y
print(f"MoE 层输出形状 {tuple(y.shape)}，和输入一样：外面看它就是一个 FFN")

# ---------- 2. 总参数 vs 激活参数（Qwen3-30B-A3B 公开配置） ----------
big = Qwen3MoeConfig(vocab_size=151936, hidden_size=2048, num_hidden_layers=48, num_attention_heads=32,
                     num_key_value_heads=4, head_dim=128, moe_intermediate_size=768, num_experts=128,
                     num_experts_per_tok=8, tie_word_embeddings=False)
with torch.device("meta"):
    m = AutoModelForCausalLM.from_config(big)
total = sum(p.numel() for p in m.parameters())
one_expert = sum(p.numel() for p in m.model.layers[0].mlp.experts[0].parameters())
idle = (big.num_experts - big.num_experts_per_tok) * one_expert * big.num_hidden_layers
print(f"\nQwen3-30B-A3B：每层 {big.num_experts} 个专家、每个 token 选 {big.num_experts_per_tok} 个，共 {big.num_hidden_layers} 层")
print(f"  一个专家 {one_expert / 1e6:.1f}M 参数；总参数 {total / 1e9:.1f}B；每个 token 用到 {(total - idle) / 1e9:.1f}B")
