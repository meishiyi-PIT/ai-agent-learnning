"""回头重讲课件 6《Transformer vs LLaMA》右图：用 MiniMind 的模型代码走一遍。

minimind_model.py 是 MiniMind 官方 model/model_minimind.py 原样拷贝（github.com/jingyaogong/minimind），
结构对齐 Qwen3：RMSNorm + GQA + RoPE + SwiGLU，Pre-Norm。

1. SwiGLU 手算：gate 决定 up 的每一维放多少过去
2. 按默认配置（minimind-3，64M）搭一个随机权重的模型，喂 5 个 token，
   用 hook 按真实调用顺序打印"第 0 层 + 最上面"的每个零件和输出形状 —— 对着图从下往上看
3. 数参数：注意力 vs FFN 各占多少

运行：cd meishiyi/09_HuggingFace && .venv/Scripts/python -X utf8 arch_train/s16_llama_walk.py
"""
import torch
import torch.nn.functional as F

from minimind_model import MiniMindConfig, MiniMindForCausalLM

# ---------- 1. SwiGLU 手算 ----------
gate = torch.tensor([2.0, -2.0, 0.0])          # gate_proj(x) 的三维
up = torch.tensor([1.0, 1.0, 1.0])             # up_proj(x) 的三维
print("SiLU(gate) =", [round(v, 2) for v in F.silu(gate).tolist()], " ReLU(gate) =", F.relu(gate).tolist())
print("SiLU(gate) * up =", [round(v, 2) for v in (F.silu(gate) * up).tolist()], "← 再经 down_proj 降回 hidden 维")

# ---------- 2. 按调用顺序走一遍 ----------
torch.manual_seed(0)
cfg = MiniMindConfig()
model = MiniMindForCausalLM(cfg).eval()
print(f"\nhidden {cfg.hidden_size}，{cfg.num_hidden_layers} 层，Q 头 {cfg.num_attention_heads} / KV 头 {cfg.num_key_value_heads}，"
      f"head_dim {cfg.head_dim}，FFN 中间维 {cfg.intermediate_size}，词表 {cfg.vocab_size}，rope_theta {cfg.rope_theta:.0e}")

watch = ["model.embed_tokens", "model.layers.0.input_layernorm", "model.layers.0.self_attn.q_proj",
         "model.layers.0.self_attn.k_proj", "model.layers.0.self_attn.v_proj", "model.layers.0.self_attn.q_norm",
         "model.layers.0.self_attn.k_norm", "model.layers.0.self_attn.o_proj", "model.layers.0.post_attention_layernorm",
         "model.layers.0.mlp.gate_proj", "model.layers.0.mlp.up_proj", "model.layers.0.mlp.down_proj",
         "model.norm", "lm_head"]
mods = dict(model.named_modules())
step = [0]


def hook(name):
    def f(_m, _inp, out):
        out = out[0] if isinstance(out, tuple) else out
        step[0] += 1
        print(f"  {step[0]:2d}. {name:42s} 输出 {tuple(out.shape)}")
    return f


for n in watch:
    mods[n].register_forward_hook(hook(n))
ids = torch.tensor([[1, 300, 301, 302, 303]])          # 5 个 token id（随便取）
with torch.no_grad():
    model(ids)

# ---------- 3. 参数分布 ----------
layer = model.model.layers[0]
attn = sum(p.numel() for p in layer.self_attn.parameters())
ffn = sum(p.numel() for p in layer.mlp.parameters())
total = sum(p.numel() for p in model.parameters())
print(f"\n一层：注意力 {attn / 1e6:.2f}M，FFN(SwiGLU) {ffn / 1e6:.2f}M；全模型 {total / 1e6:.1f}M（输入输出共用一张词表矩阵）")
