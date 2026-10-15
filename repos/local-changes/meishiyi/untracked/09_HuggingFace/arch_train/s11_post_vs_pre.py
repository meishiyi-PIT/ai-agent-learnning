"""追问：Post-Norm 到底有什么问题？它是不是没意义？

玩具实验：同样结构的小网络（每层 = 前馈网络 + 残差 + LayerNorm），只改 Norm 放的位置，
分别叠 6 / 12 / 48 层，看最后一层的输出里"最初的输入 x0"还剩多少（余弦相似度，1 = 完全一样，0 = 毫无关系）。
残差本来的承诺是"把输入原样往上传"，这个数就是在检查承诺兑现了多少。

运行：cd meishiyi/09_HuggingFace && .venv/Scripts/python -X utf8 arch_train/s11_post_vs_pre.py
"""
import torch
import torch.nn as nn

D = 256


class Block(nn.Module):
    def __init__(self, pre):
        super().__init__()
        self.pre = pre
        self.norm = nn.LayerNorm(D)
        self.ffn = nn.Sequential(nn.Linear(D, 4 * D), nn.ReLU(), nn.Linear(4 * D, D))

    def forward(self, x):
        if self.pre:
            return x + self.ffn(self.norm(x))       # Pre-Norm：门口归一化，主干道只做加法
        return self.norm(x + self.ffn(x))           # Post-Norm：先相加，再把主干道整体归一化


torch.manual_seed(0)
x0 = torch.randn(64, D)
with torch.no_grad():
    for depth in [6, 12, 48]:
        row = []
        for pre in [False, True]:
            torch.manual_seed(1)
            x = x0
            for _ in range(depth):
                x = Block(pre)(x)
            row.append(torch.cosine_similarity(x, x0, dim=-1).mean().item())
        print(f"{depth:2d} 层：Post-Norm 原稿还剩 {row[0]:.2f}，Pre-Norm 原稿还剩 {row[1]:.2f}")
