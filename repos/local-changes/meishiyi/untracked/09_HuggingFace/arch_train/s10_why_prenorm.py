"""追问：为什么 RMSNorm 要放在注意力 / 前馈网络之前？

1. 真实测量：Qwen3-0.6B 读一句话，看主干道（残差流）上的数在 28 层里怎么变大，
   以及每层进门前 RMSNorm 把它调回多大。
2. 后果演示：同一组注意力打分，数正常 vs 数放大 20 倍，softmax 之后长什么样。

运行：cd meishiyi/09_HuggingFace && .venv/Scripts/python -X utf8 arch_train/s10_why_prenorm.py
"""
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = Path(__file__).resolve().parent.parent / "models" / "Qwen3-0.6B"
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32).eval()


def rms(t):
    return t.pow(2).mean().sqrt().item()


ids = tok("人工智能正在改变世界", return_tensors="pt").input_ids
with torch.no_grad():
    hs = model(ids, output_hidden_states=True).hidden_states   # hs[i] = 第 i 层的输入（主干道上的 x）
    print("第几层 | 主干道上 x 的大小(RMS) | 进门前 RMSNorm 之后的大小")
    for i in [0, 1, 7, 14, 21, 27]:
        normed = model.model.layers[i].input_layernorm(hs[i])
        print(f"  {i:2d}   | {rms(hs[i]):10.2f}            | {rms(normed):6.2f}")

scores = torch.tensor([2.0, 1.0, 0.5, 0.0])     # 某个词对 4 个词的注意力打分
for scale in [1, 20]:
    print(f"打分放大 {scale:2d} 倍 → softmax 权重", [round(v, 3) for v in torch.softmax(scores * scale, 0).tolist()])
