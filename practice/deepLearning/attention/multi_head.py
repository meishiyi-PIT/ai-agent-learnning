"""
模块五 · 《注意力机制》第五节：多头注意力 MultiHeadedAttention
===============================================================

【5.1 为什么要多头】
    一套 W_Q/W_K/W_V = 一个"头" = 一种看词与词关系的角度。一个头只能学一种关系
    （比如"谁指代谁"），但句子里同时有主谓宾、时间地点、修饰关系……
    多头 = 并排放 n 套表，各看各的角度，最后把 n 份结果拼起来再融合一次。

【5.2 "头"是怎么切出来的——不是造 n 倍大的表，是把一张表切成 n 段】
    d_model = 词向量长度（如 8），n_head = 头数（如 2），每头分到 d_token = d_model / n_head = 4 个数。
    做法：x 乘一张 8×8 的表 Q 得到 8 个数的 q，然后把这 8 个数**切成 2 段、每段 4 个**：
        前 4 个数归头 1，后 4 个数归头 2。
    k、v 同样切。于是头 1 拿着 4 维的 q/k/v 算注意力，头 2 拿着另外 4 维的算，互不干扰。
    每头输出 4 个数，2 个头拼回 8 个数，再乘一张 8×8 的表 self.linear 融合 → 输出还是 8 个数。
    参数量和单头一样（8×8 的表还是那几张），只是算注意力时分成了 2 组各算各的。

【5.3 forward 里三个形状操作，各干一件事】（B=句数, L=词数, H=头数, d=每头维度, d_model=H×d）
    .view(B, L, H, d)       把最后一维 d_model 切成 H 段：[B, L, d_model] → [B, L, H, d]  （只是换个看法，不动数据）
    .transpose(1, 2)        把"头"提到前面：[B, L, H, d] → [B, H, L, d]
                            为什么：attention() 对最后两维 [L, d] 做矩阵乘，前面的 [B, H] 当 batch 一起广播，
                            这样 H 个头一次算完，不用写 for 循环
    attention(q, k, v)      → [B, H, L, d]，每个头各自一份结果
    .transpose(1, 2)        把"头"放回去：[B, H, L, d] → [B, L, H, d]
    .reshape(B, -1, H*d)    把 H 段拼回一条：[B, L, H, d] → [B, L, d_model]   （就是 concat）
    self.linear(concat)     各头结果再过一张表融合，形状不变

【为什么 transpose 之后要 reshape 而不是 view】
    transpose 只是改了"读取顺序"，内存里的数没挪，此时张量不连续，view 会报错；reshape 会自动拷一份再切。

【bias=False】
    Transformer 的通行做法：Q/K/V 投影不加 bias，省参数、和后面的 LayerNorm 配合更好；加上也能跑。

【课件代码勘误】
    · 课件同样直接调 attention()，需要 import。
    · 课件 attention(q, k, v, self.dropout) 传的是 nn.Dropout 模块，本项目 attention() 兼容。
    · 课件类名 MultHeadedAttention 少了个 i，这里保留原名以便和课件对照，同时提供正确拼写的别名。

运行：
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python attention/multi_head.py
"""

import torch
from torch import nn

from attention import attention


class MultHeadedAttention(nn.Module):
    def __init__(self, d_model, n_head, dropout=0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)

        assert d_model % n_head == 0, "d_model 必须能被 n_head 整除，否则切不匀"
        self.d_token = d_model // n_head      # 每个头分到几个数
        self.n_head = n_head

        # 三张 d_model×d_model 的表 —— 和单头一样多，不是 n 倍
        self.q_linear = nn.Linear(d_model, d_model, bias=False)
        self.k_linear = nn.Linear(d_model, d_model, bias=False)
        self.v_linear = nn.Linear(d_model, d_model, bias=False)
        # 各头拼接后再过一张表做融合
        self.linear = nn.Linear(d_model, d_model, bias=False)

    def forward(self, q, k, v):
        # q, k, v: [B, L, d_model]；自注意力时三个传同一个 x
        n_batchs = q.size(0)
        q_seq_len, k_seq_len, v_seq_len = q.size(1), k.size(1), v.size(1)

        # 乘表 → 切成 n_head 段 → 把头提到 batch 后面
        # [B, L, d_model] → [B, L, H, d] → [B, H, L, d]
        q = self.q_linear(q).view(n_batchs, q_seq_len, self.n_head, self.d_token).transpose(1, 2)
        k = self.k_linear(k).view(n_batchs, k_seq_len, self.n_head, self.d_token).transpose(1, 2)
        v = self.v_linear(v).view(n_batchs, v_seq_len, self.n_head, self.d_token).transpose(1, 2)

        # H 个头一次算完：attention 只看最后两维 [L, d]，前面 [B, H] 当 batch
        att, p_attn = attention(q, k, v, self.dropout)     # att: [B, H, L, d]

        # 把头放回去再拼成一条：[B, H, L, d] → [B, L, H, d] → [B, L, d_model]
        concat = att.transpose(1, 2).reshape(n_batchs, -1, self.n_head * self.d_token)
        output = self.linear(concat)                       # 融合，形状不变
        return output


MultiHeadedAttention = MultHeadedAttention   # 正确拼写的别名


def demo_shapes():
    print("=" * 60)
    print("demo 1：跟踪 forward 里每一步的形状（d_model=8, n_head=2）")
    print("=" * 60)
    mha = MultHeadedAttention(d_model=8, n_head=2, dropout=0.0)
    x = torch.randn(2, 3, 8)                  # 2 句，每句 3 个词，每词 8 个数
    B, L = x.shape[0], x.shape[1]
    H, d = mha.n_head, mha.d_token
    print(f"x                    {tuple(x.shape)}   [B, L, d_model]")

    q = mha.q_linear(x)
    print(f"q_linear(x)          {tuple(q.shape)}   乘表，形状不变")
    q = q.view(B, L, H, d)
    print(f".view(B, L, H, d)    {tuple(q.shape)}   最后一维 8 切成 2 段×4")
    q = q.transpose(1, 2)
    print(f".transpose(1, 2)     {tuple(q.shape)}   头提到前面 [B, H, L, d]")

    k = mha.k_linear(x).view(B, L, H, d).transpose(1, 2)
    v = mha.v_linear(x).view(B, L, H, d).transpose(1, 2)
    att, p = attention(q, k, v)
    print(f"attention → att      {tuple(att.shape)}   每个头各一份 [B, H, L, d]")
    print(f"attention → p_attn   {tuple(p.shape)}   每个头各一张 L×L 分数表")
    concat = att.transpose(1, 2).reshape(B, -1, H * d)
    print(f"transpose+reshape    {tuple(concat.shape)}   拼回 [B, L, d_model]")
    out = mha.linear(concat)
    print(f"linear(concat)       {tuple(out.shape)}   融合，和 x 同形状")

    print("\n头 0 和头 1 给第 0 句第 0 个词的比例（两个头看法不同）：")
    print("  头 0:", [round(t, 3) for t in p[0, 0, 0].tolist()])
    print("  头 1:", [round(t, 3) for t in p[0, 1, 0].tolist()])


def demo_params():
    print("\n" + "=" * 60)
    print("demo 2：多头参数量 = 单头参数量（不是 n 倍）")
    print("=" * 60)
    for h in (1, 2, 4):
        m = MultHeadedAttention(d_model=8, n_head=h)
        n = sum(p.numel() for p in m.parameters())
        print(f"n_head={h}: 参数 {n} = 4 张 8×8 的表")


def demo_courseware():
    print("\n" + "=" * 60)
    print("demo 3：课件原样的调用")
    print("=" * 60)
    mha = MultHeadedAttention(8, 2)
    q = k = v = torch.randn(2, 3, 8)
    print(mha(q, k, v).shape)                 # torch.Size([2, 3, 8])


if __name__ == "__main__":
    torch.manual_seed(0)
    demo_shapes()
    demo_params()
    demo_courseware()
