"""
模块五 · 《5.Transformer》2.3–2.5：自注意力分不清语序 → 正余弦位置编码
======================================================================
（第 3 站 / 共 8 站。上一站：Embedding × √d。这一站填架构图 "+ 位置编码" 那格。下一站：相加为什么不打架。）

【先补数学：sin / cos 只需要这一个画面】
    一个点在半径为 1 的圆上转，转过的角度叫 x（单位是弧度，转一整圈 = 2π ≈ 6.28）。
        cos(x) = 这个点的横坐标      sin(x) = 这个点的纵坐标
    所以两者永远在 [-1, 1] 之间，而且转一整圈回到原处（周期 2π）。
    手算值（记这几个就够）：
        x=0    → sin 0,     cos 1
        x=1    → sin 0.841, cos 0.540
        x=2    → sin 0.909, cos -0.416
        x=3    → sin 0.141, cos -0.990
        x=0.01 → sin 0.010, cos 1.000      （角度很小时 sin x ≈ x，cos ≈ 1）
    "频率 / 波长"：sin(x / 100) 里的 100 是"刻度"。x 走 1 格角度只走 0.01，要走 628 格才转完一圈 —— 慢表针；
    sin(x / 1) 走 6.28 格就转一圈 —— 快表针。除数越大，转得越慢，波长越长。

【2.3 自注意力"脸盲"：把句子里的词换顺序，输出只是跟着换行，数值一个不变】
    自注意力对每个词做的是"我的 q 和所有词的 k 点积 → softmax → 按比例混合所有词的 v"。
    这套计算里没有任何一步用到"第几个"：k、v 是一堆无序的 (k, v) 对，你把它们洗牌，
    每个词算出来的新向量一模一样（demo 1 用课件的数据验证）。
    但"狗咬我"和"我咬狗"不是一回事，所以必须把位置信息塞进向量本身。

【2.4 正余弦位置编码：给每个位置造一枚"多刻度指纹"】
    公式（pos = 词在句中的位置 0,1,2,…；i = 维度对的编号；d = d_model）：
        PE(pos, 2i)   = sin( pos / 10000^(2i/d) )     偶数维放 sin
        PE(pos, 2i+1) = cos( pos / 10000^(2i/d) )     奇数维放 cos，除数和偶数维相同
    每一对维度 (2i, 2i+1) 就是一个表盘：偶数维记纵坐标、奇数维记横坐标，一对合起来就是"表针指向哪"。
    i 越大除数越大，表针转得越慢。d 维 = d/2 个快慢不同的表盘。

    手算 d=4（两个表盘，除数分别是 10000^(0/4)=1 和 10000^(2/4)=100）：
        pos=0 → [sin 0,   cos 0,   sin 0,    cos 0   ] = [ 0,     1,      0,     1    ]
        pos=1 → [sin 1,   cos 1,   sin 0.01, cos 0.01] = [ 0.841, 0.540,  0.010, 1.000]
        pos=2 → [sin 2,   cos 2,   sin 0.02, cos 0.02] = [ 0.909, -0.416, 0.020, 1.000]
        pos=3 → [sin 3,   cos 3,   sin 0.03, cos 0.03] = [ 0.141, -0.990, 0.030, 1.000]
    前两维（快表盘）每走一步大变，后两维（慢表盘）几乎没动 —— 快针分辨相邻位置，慢针分辨远距离。

    直觉一：时钟。只看秒针分不清 1:00:05 和 2:00:05，只看时针分不清 1:00:05 和 1:00:06；
            秒针+分针+时针一起读，每个时刻唯一。d/2 个表盘一起读，每个 pos 唯一。
    直觉二：二进制计数。0=000, 1=001, 2=010, 3=011 …最低位每步翻转、次低位每 2 步翻转、最高位每 4 步翻转。
            sin/cos 就是这个"不同位以不同速度翻转"的连续平滑版本，而且取值不会像 pos 本身那样越来越大。

    为什么不直接用 pos = 0,1,2,…,511 当编码？数值无上界，第 500 个词的位置数会把词向量彻底盖住；
    除以句长归一化又会让"第 3 个词"在 10 词句和 100 词句里编码不同。sin/cos 有界、和句长无关。

    相对位置：把表针转 k 格这个动作，和当前指向哪无关。所以 PE(pos+k) 总能由 PE(pos) 做同一个固定变换得到，
    模型想学"隔 k 个词"的关系很容易。demo 3 用一个更好看的现象验证：PE(pos)·PE(pos+k) 的点积只和 k 有关。

【代码逐行（张量形状是关键）】
    pos      = arange(0, max_len).unsqueeze(1)                 (max_len, 1)     一列位置号
    div_term = 10000 ** (arange(0, d, 2) / d)                   (d/2,)           每个表盘的除数 [1, 100, …]
    pos / div_term                                              (max_len, d/2)   广播：每个位置 ÷ 每个除数 → 每个表盘的角度
    pe[:, 0::2] = sin(...)   pe[:, 1::2] = cos(...)             偶数列放 sin、奇数列放 cos
    pe = pe.unsqueeze(0)                                        (1, max_len, d)  前面补 batch 维，好和 (batch, seq, d) 相加
    forward: x + pe[:, :x.size(1)]                              只截到当前句长，靠广播加到 batch 里每一句上
    课件 forward 里那句 print(self.pe[...]) 是调试残留，这里删掉。

【Python 小补】
    a[0::2]  = 从 0 开始、到末尾、步长 2（偶数下标）；a[1::2] 奇数下标。写法是 start:stop:step。
    (max_len, 1) 和 (d/2,) 相除 → 自动扩成 (max_len, d/2)，这叫广播：长度为 1 的维度会被复制去配对方。
    register_buffer("pe", pe)：登记为"模型的一部分但不训练"。它会进 state_dict（随模型保存/加载/.to(device)），
    但不在 model.parameters() 里，优化器碰不到。nn.Parameter 则两者都在。demo 4 对比。

【2.5 优点四条 + 现在的做法】
    唯一（每个 pos 指纹不同）/ 相对位置可推 / 零参数 / 可外推（pos 再大公式也算得出）。
    现代 LLM 不再用它：GPT-2 用可学习的位置表（nn.Embedding(max_len, d)），LLaMA/Qwen/DeepSeek 用 RoPE
    （把"转表针"直接作用在 q、k 上而不是加到词向量上）。原理一脉相承：都是用"转角"表示位置。

运行：
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python transformer/positional.py
"""

import math

import torch
from torch import nn


class PositionalEncoding(nn.Module):
    """课件原版（去掉调试 print）。"""

    def __init__(self, d_model, max_len=5000, dropout=0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)

        pe = torch.zeros(max_len, d_model)                                        # (max_len, d)
        pos = torch.arange(0, max_len).unsqueeze(1)                               # (max_len, 1)
        div_term = torch.pow(10000, torch.arange(0, d_model, 2).float() / d_model)  # (d/2,)
        pe[:, 0::2] = torch.sin(pos / div_term)                                   # 偶数列
        pe[:, 1::2] = torch.cos(pos / div_term)                                   # 奇数列
        pe = pe.unsqueeze(0)                                                      # (1, max_len, d)
        self.register_buffer("pe", pe)                                            # 不训练、但随模型保存

    def forward(self, x):
        # x: (batch, seq_len, d) ；只截前 seq_len 个位置，广播加到每一句
        x = x + self.pe[:, :x.size(1)]
        return self.dropout(x)


def demo_permutation():
    print("=" * 64)
    print("demo 1：自注意力脸盲 —— 前两个词对调，输出只是前两行对调")
    print("=" * 64)
    q1 = torch.tensor([[0., 1., 2., 1., 5.], [3., 9., 3., 8., 2.], [2., 3., 1., 5., 6.]])
    k1 = torch.tensor([[3., 2., 1., 5., 5.], [1., 5., 5., 0., 1.], [0., 8., 9., 6., 1.]])
    v1 = torch.tensor([[7., 3., 1., 2., 1.], [4., 7., 1., 1., 9.], [5., 7., 1., 9., 8.]])
    swap = [1, 0, 2]                                   # 第 0、1 行对调
    q2, k2, v2 = q1[swap], k1[swap], v1[swap]

    def simple_attention(q, k, v):
        scores = q @ k.transpose(-1, -2)
        return torch.softmax(scores, dim=-1) @ v

    out1, out2 = simple_attention(q1, k1, v1), simple_attention(q2, k2, v2)
    print("原顺序输出:\n", out1)
    print("对调后输出:\n", out2)
    print("对调后 == 原输出把行对调?", torch.allclose(out1[swap], out2))
    print("→ 数值一个没变，模型完全不知道谁在前谁在后。")


def demo_hand_calc():
    print("\n" + "=" * 64)
    print("demo 2：d_model=4 手算对照（两个表盘，除数 1 和 100）")
    print("=" * 64)
    pe = PositionalEncoding(d_model=4, max_len=10, dropout=0.0).pe[0]   # (10, 4)
    div = torch.pow(10000, torch.arange(0, 4, 2).float() / 4)
    print("div_term =", div.tolist(), " ← 两个表盘的除数")
    for p in range(4):
        print(f"pos={p}: {[round(v, 3) for v in pe[p].tolist()]}")
    print("→ 对照 docstring 里的手算；前两维每步大变（快针），后两维几乎不动（慢针）。")


def demo_dials():
    print("\n" + "=" * 64)
    print("demo 3：多刻度表盘 —— d_model=8 的 4 个表盘各转多快；相对位置只和 k 有关")
    print("=" * 64)
    d = 8
    div = torch.pow(10000, torch.arange(0, d, 2).float() / d)
    for i, dv in enumerate(div.tolist()):
        print(f"表盘 {i}（维 {2*i},{2*i+1}）：除数 {dv:8.2f}，转一圈要走 {2*math.pi*dv:8.1f} 个位置")
    pe = PositionalEncoding(d_model=d, max_len=100, dropout=0.0).pe[0]
    print("\n维 0（最快针）在 pos 0..5：", [round(v, 2) for v in pe[:6, 0].tolist()])
    print("维 6（最慢针）在 pos 0..5：", [round(v, 4) for v in pe[:6, 6].tolist()])
    print("\nPE(pos)·PE(pos+3) 在不同 pos 上：",
          [round((pe[p] @ pe[p + 3]).item(), 4) for p in (0, 10, 40, 80)])
    print("PE(pos)·PE(pos+1) 在不同 pos 上：",
          [round((pe[p] @ pe[p + 1]).item(), 4) for p in (0, 10, 40, 80)])
    print("→ 同一个间隔 k，不管从哪个 pos 出发，点积都一样：编码里带着'相对距离'。")


def demo_buffer_vs_parameter():
    print("\n" + "=" * 64)
    print("demo 4：register_buffer vs nn.Parameter")
    print("=" * 64)

    class M(nn.Module):
        def __init__(self):
            super().__init__()
            self.weight = nn.Parameter(torch.randn(2, 2))
            self.register_buffer("running_mean", torch.zeros(2))

    m = M()
    print("state_dict 的 key：", list(m.state_dict().keys()), " ← 两个都会被保存")
    print("parameters() 的个数：", len(list(m.parameters())), " ← 只有 weight 会被优化器更新")

    pos = PositionalEncoding(d_model=8, max_len=50)
    x = torch.randn(2, 3, 8)                                    # 2 句 × 3 词 × 8 维
    print("位置编码层的可训练参数个数：", sum(p.numel() for p in pos.parameters()), " ← 零参数")
    print("输入", tuple(x.shape), "→ 输出", tuple(pos(x).shape), " ← 形状不变，只是加了指纹")


def demo_with_pe():
    print("\n" + "=" * 64)
    print("demo 5：号码牌的用处 —— 加上位置编码后，换序的句子输出不再只是换行")
    print("=" * 64)
    torch.manual_seed(0)
    d = 4
    words = torch.randn(3, d)                          # 三个词的词向量（随机代替真实 Embedding）
    swap = [1, 0, 2]
    pe = PositionalEncoding(d_model=d, max_len=10, dropout=0.0).pe[0, :3]   # 位置 0,1,2 的号码牌

    def self_attention(x):                              # 最简自注意力：q=k=v=x
        return torch.softmax(x @ x.T / d ** 0.5, dim=-1) @ x

    out_a = self_attention(words)                       # 不加号码牌，原顺序
    out_b = self_attention(words[swap])                 # 不加号码牌，前两词对调
    print("不加号码牌：对调后 == 原输出换行?", torch.allclose(out_a[swap], out_b, atol=1e-6))

    out_c = self_attention(words + pe)                  # 加号码牌，原顺序：词向量 + 该位置的牌
    out_d = self_attention(words[swap] + pe)            # 加号码牌，对调后：词换了位置，牌不换
    print("加了号码牌：对调后 == 原输出换行?", torch.allclose(out_c[swap], out_d, atol=1e-6))
    print("→ 同一个词换了位置，加上不同的牌，注意力算出的结果就不同了：模型从此分得清语序。")


if __name__ == "__main__":
    torch.manual_seed(0)
    demo_permutation()
    demo_hand_calc()
    demo_dials()
    demo_buffer_vs_parameter()
    demo_with_pe()
