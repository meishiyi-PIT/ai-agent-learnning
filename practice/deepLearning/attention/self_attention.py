"""
模块五 · 《注意力机制》第四节 4.5：SelfAttention —— 三张表 + attention()
========================================================================

【和 attention() 的分工】
    attention(q, k, v)   只做"打分 → 缩放 → softmax → 加权和"，没有任何可训练参数
    SelfAttention        负责把输入 x 变成 q、k、v（乘三张表），再调 attention()
    所以注意力层的**全部参数 = 三张表**（q_linear / k_linear / v_linear 的 weight）。

【"自"注意力就一句话】
    q、k、v 都从同一份 x 算出来：句子里每个词既是查的人也是被查的人。
    forward 里 q = self.q_linear(x)、k = self.k_linear(x)、v = self.v_linear(x)，三条路同一个起点。

【nn.Linear 在这里就是"一行数乘一张表"】
    Linear(D, D) 内部是一张 D×D 的表 W（外加一个 bias 向量）。x 是 [seq_len, D]，
    self.q_linear(x) = x @ Wᵀ + b —— 每个词的向量各自乘同一张表，得到每个词的 q。
    三个 Linear 互不共享参数，分别学"怎么提问 / 怎么被找 / 给什么"。

【形状】
    x         [batch, seq_len, D]
    q/k/v     [batch, seq_len, D]      Linear 只改最后一维，这里 D→D 没变
    scores    [batch, seq_len, seq_len] 每句话一张"词×词"分数表
    输出      [batch, seq_len, D]      进几行出几行，每行带上了上下文

【课件代码勘误】
    课件 4.5 直接调用 attention()，但该函数定义在第三节的另一段代码里，单独跑 4.5 会 NameError；
    这里显式 import。另外本项目的 attention() 多返回一个 p_attn（方便观察比例），所以要接两个返回值。

运行：
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python attention/self_attention.py
"""

import torch
import torch.nn as nn

from attention import attention


class SelfAttention(nn.Module):
    """自注意力：Q、K、V 由同一份输入投影而来。"""

    def __init__(self, hidden_dim):
        super().__init__()
        self.hidden_dim = hidden_dim
        # 三张互不共享的表
        self.q_linear = nn.Linear(hidden_dim, hidden_dim)
        self.k_linear = nn.Linear(hidden_dim, hidden_dim)
        self.v_linear = nn.Linear(hidden_dim, hidden_dim)

    def forward(self, x):
        # x: [batch, seq_len, hidden_dim]
        q = self.q_linear(x)          # 我要找什么
        k = self.k_linear(x)          # 我拿什么被找
        v = self.v_linear(x)          # 找到我后拿走什么
        out, p_attn = attention(q, k, v)
        return out, p_attn


def demo_trace():
    """把三张表的内容和 x 乘表的结果逐个打出来，看 q/k/v 是怎么从同一个 x 变出来的。"""
    print("=" * 60)
    print("demo 0：跟踪 q_linear / k_linear / v_linear 在干什么")
    print("=" * 60)
    net = SelfAttention(2)
    # 平时表里是随机数，这里手动写死成整数，方便手算对照；bias 全设 0 先不管它
    with torch.no_grad():
        net.q_linear.weight.copy_(torch.tensor([[1.0, 0.0],
                                                [0.0, 1.0]]))     # 表 Q：什么都不改
        net.k_linear.weight.copy_(torch.tensor([[0.0, 1.0],
                                                [1.0, 0.0]]))     # 表 K：两个数对调
        net.v_linear.weight.copy_(torch.tensor([[2.0, 0.0],
                                                [0.0, 2.0]]))     # 表 V：全部翻倍
        for lin in (net.q_linear, net.k_linear, net.v_linear):
            lin.bias.zero_()

    x = torch.tensor([[[1.0, 2.0],       # 词 1
                       [3.0, 0.0],       # 词 2
                       [0.0, 1.0]]])     # 词 3      形状 [1 句, 3 词, 2 个数]
    print("x（一句话 3 个词，每词 2 个数）：")
    print(x[0])

    q = net.q_linear(x)
    k = net.k_linear(x)
    v = net.v_linear(x)
    print("\nq = x 乘表 Q（表 Q 什么都不改，所以 q 和 x 一样）：")
    print(q[0])
    print("k = x 乘表 K（表 K 把每个词的两个数对调）：")
    print(k[0])
    print("v = x 乘表 V（表 V 把每个数翻倍）：")
    print(v[0])
    print("\n→ 同一句话 x，乘三张不同的表，得到三个不同版本：q 用来提问，k 用来被找，v 用来被拿。")
    print("  表里的数真实训练时不是 0/1/2，是随机初始化再被 loss 磨出来的。")

    out, p = attention(q, k, v)
    print("\n然后 attention(q, k, v) 就是前面那四行 → 输出形状", tuple(out.shape), "和 x 一样")


if __name__ == "__main__":
    demo_trace()
    print()

    torch.manual_seed(0)
    x = torch.rand(3, 2, 4)          # batch=3，每句 2 个词，词向量 4 维
    net = SelfAttention(4)
    out, p = net(x)
    print("输入 x   :", tuple(x.shape))
    print("输出 out :", tuple(out.shape), " ← 和输入一样，进几行出几行")
    print("p_attn   :", tuple(p.shape), " ← [batch, 词, 词]，每句一张 2x2 分数表")

    print("\n注意力层的全部参数（就是三张表 + 三个 bias）：")
    total = 0
    for name, param in net.named_parameters():
        print(f"  {name:16} {tuple(param.shape)}")
        total += param.numel()
    print("  参数总数 =", total, " = 3 × (4×4 + 4)")

    print("\n第 0 句的 p_attn（每行和为 1）：")
    print(p[0])
