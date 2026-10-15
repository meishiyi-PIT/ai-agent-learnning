"""
模块五 · 第 6 节 · 6.1 网络结构：TextClassifier
====================================================
课件"重要步骤 1：带有词向量的神经网络设计"。

【它在整条流水线里的位置】
    csv → 切词 → 查 ID → 补 pad → [B, L] 整数张量 → ★本文件★ → [B, 4] 类别分数
前三步在 data.py / utils.py，本文件只管"整数张量进、类别分数出"。

【forward 三行 = 三个形状变化】（B=一批几句，L=每句补齐后几个词，D=embed_dim）
    x = self.embedding(x)      [B, L]     -> [B, L, D]   每个 ID 查表长胖成 D 个数（第 5 节）
    x = torch.sum(x, dim=1)    [B, L, D]  -> [B, D]      L 个词向量竖着加成 1 个句向量
    x = self.fc(x)             [B, D]     -> [B, 4]      Linear 链打 4 个类别分数

【为什么用 sum 聚合 / 为什么不能全加成一个数】见学习笔记 Q&A"相加"条目。一句话：
按位置逐列相加，D 个位置各自汇总各自的信息，结果仍是 D 个数；dim=1 就是"沿 L 方向压"。

【fc 为什么是四层】不是必须。一个 Linear(D, 4) 就能分类；堆多层 + ReLU 只是让模型能
"先算中间结论再算最终结论"。128→64→32→4 是漏斗形习惯，无理论依据。
    Linear 后接 BatchNorm1d（不是 2d：这里是二维张量 [B, 特征]）再 ReLU，
    最后一层 Linear(32, 4) 不接 BN/ReLU —— 它输出的是 logits，直接交给 CrossEntropyLoss
    （不要在这里加 Softmax，理由见 CNN 那节笔记"为什么模型末尾不放 Softmax"）。

【padding_idx 在这里的收益兑现】<pad> 行恒为全 0，sum 时加进去等于没加，
所以短句补多少个 pad 都不会污染句向量。这是第 5 节 5-c 讲的设计目的落地的地方。

【课件勘误】
  · 课件注释写"线性层的大小是 embed_dim*num_classes，例如 128*4"——那是"一个 Linear"的情况，
    与紧接着的四层 Sequential 不符；实际第一层是 Linear(embed_dim, 128)。
  · BatchNorm1d 在训练模式下要求 batch >= 2；__main__ 里 x 是 2 条样本刚好够，改成 1 条会报错。

运行：
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python text_cls/net.py
"""

import torch
import torch.nn as nn


class TextClassifier(nn.Module):
    def __init__(self, vocab_size, embed_dim, num_classes, padding_idx):
        super().__init__()
        # 第 5 节的那张表：vocab_size 行 × embed_dim 列，padding_idx 那行恒为 0
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=padding_idx)

        # 分类头：每个 Linear 只改最后一维，上一层 out 必须等于下一层 in
        self.fc = nn.Sequential(
            nn.Linear(embed_dim, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),

            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),

            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),

            nn.Linear(32, num_classes),   # 输出 logits，不加 Softmax
        )

    def forward(self, x):
        x = self.embedding(x)          # [B, L]    -> [B, L, D]
        x = torch.sum(x, dim=1)        # [B, L, D] -> [B, D]
        x = self.fc(x)                 # [B, D]    -> [B, num_classes]
        return x


if __name__ == "__main__":
    model = TextClassifier(vocab_size=5000, embed_dim=128, num_classes=4, padding_idx=0)
    print(model)

    # 模拟一批：2 句话，每句 6 个 ID，ID 随机取自 [0, 5000)
    x = torch.randint(0, 5000, (2, 6))
    print("\n输入 x:", tuple(x.shape))
    print(x)

    # 逐步打印三个形状，和 docstring 里的表对照
    with torch.no_grad():
        e = model.embedding(x)
        s = torch.sum(e, dim=1)
        out = model.fc(s)
    print("\nembedding 后:", tuple(e.shape))
    print("sum(dim=1) 后:", tuple(s.shape))
    print("fc 后:", tuple(out.shape))
    print(out)
