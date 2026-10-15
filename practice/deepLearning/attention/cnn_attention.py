"""
模块五 · 《注意力机制》第六节：给 CNN 装上注意力
==================================================

【核心思路：把特征图"读"成一句话】
    卷积吐出的特征图 [N, C, H, W]：N 张图、每张 C 层通道、H×W 个位置。
    注意力要的是 [batch, seq_len, d_model]：几句话、每句几个词、每词几个数。
    对应关系：
        一张图         = 一句话
        一个空间位置    = 一个"词"        → seq_len = H×W
        该位置的 C 个通道值 = 这个词的向量  → d_model = C
    于是特征图 [1, 256, 20, 20] 变成一句 400 个"词"、每词 256 个数的"话"，直接喂自注意力。

【forward 里两步形状操作】
    x.permute(0, 2, 3, 1)             [N, C, H, W] → [N, H, W, C]   把通道挪到最后（词向量要在最后一维）
    x.reshape(N, -1, C)               [N, H, W, C] → [N, H*W, C]    H×W 个位置拍平成一串"词"
    然后 self.attention(x, x, x)      自注意力，q=k=v 都是这 400 个位置
    x.reshape(-1, 400*256)            [N, 400, 256] → [N, 102400]   拍平接分类头

【为什么要加这层】
    卷积核是"近视眼"：3×3 一次只看周围 9 格，图上相隔很远的两个位置要靠堆很多层才能建立联系
    （CNN 笔记：感受野 = 1 + 2L）。注意力让任意两个位置一次点积直达——给 CNN 补上全局视野。
    例："果皮颜色"和"果柄形状"在图上离得远，纯卷积很难把它们配对，注意力一步就能。

【特征图尺寸 20×20 怎么来的】（输入 112×112，卷积不加 padding 每层减 2，池化减半）
    112 →conv→ 110 →pool→ 55 →conv→ 53 →pool→ 26 →conv→ 24 →conv→ 22 →conv→ 20
    所以 fc 的输入是 400 × 256 = 102400。改输入尺寸，这个数要跟着改（同 CNN 笔记 "Linear(128*4*4) 数字哪来的"）。

【课件代码的两个问题】
  1. 课件注释里保留了 `#self.attention = nn.MultiheadAttention(embed_dim=256, num_heads=4)`，
     若启用它，必须加 batch_first=True（见 official.py 勘误 1），且它返回 (out, weights) 两个值，
     forward 里要写 x, _ = self.attention(x, x, x)。
  2. `x.reshape(-1, 400*256)` 把 400 和 256 写死，比 `x.reshape(x.size(0), -1)` 脆弱；这里改成后者。
     另外 102400 → num_classes 这一层参数 61 万，比整个卷积主干还大，实际项目会先做全局平均池化再接 fc。

【Python 语法点】
    permute(0, 2, 3, 1)   按给定顺序重排所有维度（transpose 一次只能换两个）
    reshape(N, -1, C)     -1 = "这一维你自己算"

运行：
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python attention/cnn_attention.py
"""

import torch
import torch.nn as nn

from multi_head import MultHeadedAttention


class CNNWithAttention(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        # 轻量卷积主干：五层卷积逐步加深通道，Conv 后统一 BN + ReLU
        self.conv_layers = nn.Sequential(
            nn.Conv2d(3, 16, 3, bias=False),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2),

            nn.Conv2d(16, 32, 3, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),

            nn.Conv2d(32, 64, 3, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(),

            nn.Conv2d(64, 128, 3, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(),

            nn.Conv2d(128, 256, 3, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(),
        )
        # 每个空间位置当一个 token，256 个通道值就是它的向量
        self.attention = MultHeadedAttention(d_model=256, n_head=4)
        # 特征图 20×20=400 个位置 × 256 → 分类
        self.fc = nn.Linear(400 * 256, num_classes)

    def forward(self, x):
        x = self.conv_layers(x)                     # [N, 256, 20, 20]   N C H W
        x = x.permute(0, 2, 3, 1)                   # [N, 20, 20, 256]   N H W C
        x = x.reshape(x.size(0), -1, x.size(-1))    # [N, 400, 256]      N 位置 C  = [batch, seq_len, d_model]
        x = self.attention(x, x, x)                 # [N, 400, 256]      自注意力，每个位置看全图
        x = x.reshape(x.size(0), -1)                # [N, 102400]
        x = self.fc(x)                              # [N, num_classes]
        return x


if __name__ == "__main__":
    model = CNNWithAttention(6)
    x = torch.randn(2, 3, 112, 112)                 # BatchNorm 训练模式要求 batch >= 2
    print("输入:", tuple(x.shape))
    with torch.no_grad():
        f = model.conv_layers(x)
        print("卷积后特征图:", tuple(f.shape), " [N, C, H, W]")
        f = f.permute(0, 2, 3, 1)
        print("permute 后  :", tuple(f.shape), " [N, H, W, C]")
        f = f.reshape(f.size(0), -1, f.size(-1))
        print("reshape 后  :", tuple(f.shape), " [batch, seq_len=400 个位置, d_model=256]  ← 一张图变成一句 400 词的话")
        f = model.attention(f, f, f)
        print("注意力后    :", tuple(f.shape), " 形状不变，每个位置掺进了全图信息")
        y = model(x)
    print("最终输出    :", tuple(y.shape))
    print("fc 参数量   :", model.fc.weight.numel(), " (102400×6，比整个卷积主干还大)")
