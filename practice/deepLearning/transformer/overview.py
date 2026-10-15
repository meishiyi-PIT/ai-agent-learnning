"""
模块五 · 《5.Transformer》第一章：架构全景 —— Transformer 到底要解决什么问题
==========================================================================

【整本课件的地图】（8 站；✅ = 《注意力机制》课件已学过、只需对号入座；🆕 = 本课件新内容）
    1 🆕 全景：Seq2Seq 问题 / RNN 的两个死穴 / Transformer 三句话 / 编码器-解码器图      ← 本文件
    2 🆕 Embedding + 为什么乘 √d_model                                    （课件 2.1–2.2）
    3 🆕 自注意力分不清语序 → 正余弦位置编码                                （2.3–2.5）
    4 🆕 词向量 + 位置编码直接相加为什么不打架                              （2.6）
    5 ✅ 多头（复习）+ 🆕 Padding Mask + ✅ 缩放点积注意力（复习）            （第三章）
    6 🆕 残差 / LayerNorm / FFN                                          （第四章）
    7 🆕 Encoder 组装 / 三角掩码 / Decoder / 交叉注意力                    （第五章 5.1–5.4）
    8 🆕 输出层 + 温度 / 整机拼装 / Xavier / 官方 nn.Transformer            （5.5–5.6、第六章）

【1.1 Seq2Seq 是"问题"，不是"模型"】
    输入一个序列，输出另一个序列：翻译、摘要、客服回复、代码生成……都是这一类问题。
    2017 年之前的主流解法是 RNN（循环神经网络）：一个词一个词地读，把读到的信息压进一个
    "隐藏状态" h 里往下传（Java 视角：一个 for 循环，h 是循环变量，每轮 h = f(h, 当前词)）。

【RNN 的两个死穴 —— demo 1 / demo 3 各演示一个】
    死穴 1：传话游戏丢信息。h 每传一步都要"乘一次"，第 1 个词的信息到第 20 个词时被连乘了 19 次，
            系数 < 1 就衰减到几乎为 0（消失），> 1 就炸到无穷大（爆炸）。这叫"长距离依赖丢失"。
    死穴 2：天生串行。第 t 步必须等第 t-1 步算完，GPU 有几千个核也只能一个一个来。

【Transformer 的解法：三句话】
    1. 用注意力替代循环 —— 第 20 个词看第 1 个词，就是算一次 q_20 · k_1，中间不经过任何传递，
       权重和"隔多远"无关（demo 2）。
    2. 用位置编码补顺序 —— 注意力本身不知道谁在前谁在后（第 3 站证明），所以要额外把位置加进去。
    3. 全并行 —— 所有词的 q·k 打分是一次矩阵乘法 Q @ Kᵀ，整句一起算（demo 3）。

【1.2–1.3 全是已学内容，对号入座即可】
    "样本相关性用点积算、有方向（谁问谁）、先乘 W_Q/W_K/W_V 再算" ——
    就是 attention/attention.py 和 attention/self_attention.py 里的东西，本课件不再重讲。

【1.4 架构图（用文字画一遍，后面 7 站就是把这张图从上到下填满）】

        源句 token 索引                          目标句 token 索引（右移一位，开头补 <bos>）
             │                                          │
        Embedding × √d_model  ← 第 2 站            Embedding × √d_model
             + 位置编码       ← 第 3、4 站               + 位置编码
             │                                          │
     ┌──── Encoder 层 × N ────┐               ┌──── Decoder 层 × N ─────────────┐
     │ 多头自注意力（看全句）   │ ← 第 5 站     │ 掩码多头自注意力（只准看前文）     │ ← 第 7 站
     │   + 残差 + LayerNorm    │ ← 第 6 站     │   + 残差 + LayerNorm             │
     │ FFN + 残差 + LayerNorm  │   memory      │ 交叉注意力：q = 自己，k/v = memory │ ← 第 7 站
     └─────────────────────────┘ ──────────►   │   + 残差 + LayerNorm             │
                                               │ FFN + 残差 + LayerNorm           │
                                               └──────────────────────────────────┘
                                                            │
                                               Linear(d_model → 目标词表大小) + softmax   ← 第 8 站
                                                            │
                                               每个位置"下一个词是谁"的概率分布

    一句话分工：Encoder 负责"读懂"源句（产出 memory）；Decoder 负责"边看 memory 边一个词一个词地写"。
    维度守恒铁律：图里每一个箭头上的向量长度都是 d_model（论文 512），进什么形状出什么形状。

运行：
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python transformer/overview.py
"""

import time

import torch


def demo_rnn_decay():
    print("=" * 64)
    print("demo 1：RNN 传话游戏 —— 第 1 个词的信息传到第 T 个词还剩多少")
    print("=" * 64)
    # 最简 RNN：h_t = w * h_{t-1} + x_t（真实 RNN 的 w 是矩阵、外面还套 tanh，但"连乘"这个本质一样）
    # 只让第 1 个词带信号（x_1 = 1，其余 0），看它在 h_T 里还剩多少 —— 答案就是 w^(T-1)
    T = 20
    x = torch.zeros(T)
    x[0] = 1.0
    for w in (0.8, 1.0, 1.2):
        h = 0.0
        trace = []
        for t in range(T):                    # 串行：必须一步一步来
            h = w * h + x[t].item()
            trace.append(h)
        print(f"w={w}: 第1词的信息在 h_1/h_5/h_10/h_20 里分别剩 "
              f"{trace[0]:.3f} / {trace[4]:.3f} / {trace[9]:.3f} / {trace[19]:.3f}"
              f"   （手算：{w}^19 = {w ** 19:.4f}）")
    print("→ w<1 消失、w>1 爆炸，只有 w 恰好=1 才不丢；训练出来的 w 不可能恰好是 1。")


def demo_attention_distance_free():
    print("\n" + "=" * 64)
    print("demo 2：注意力看第 1 个词和看第 19 个词，代价一样、权重只看内容不看距离")
    print("=" * 64)
    torch.manual_seed(0)
    T, d = 20, 4
    k = torch.randn(T, d)
    k[18] = k[0]                              # 让第 19 个词的 key 和第 1 个词完全一样
    q_last = torch.randn(d)                   # 第 20 个词发出的 query
    scores = k @ q_last                       # 20 个点积，一次算完
    weights = torch.softmax(scores, dim=0)
    print(f"第20个词分给 第1词 的权重 = {weights[0]:.4f}")
    print(f"第20个词分给 第19词 的权重 = {weights[18]:.4f}   ← 内容相同 → 权重相同，隔 18 个位置毫无影响")
    print(f"分给第2~18词的权重之和 = {weights[1:18].sum():.4f}")


def demo_serial_vs_parallel():
    print("\n" + "=" * 64)
    print("demo 3：串行 for 循环 vs 一次矩阵乘法")
    print("=" * 64)
    T, d = 1024, 64
    x = torch.randn(T, d)
    W = torch.randn(d, d) * 0.1
    U = torch.randn(d, d) * 0.1

    def rnn_pass():
        h = torch.zeros(d)
        for t in range(T):                    # RNN：1024 步必须排队，第 t 步等第 t-1 步
            h = torch.tanh(W @ h + U @ x[t])
        return h

    def attn_scores():
        return x @ x.T                        # 注意力：1024×1024 个两两打分，一条语句

    def best_of(fn, n=5):                     # 各跑 5 次取最快，排除第一次的预热开销
        best = float("inf")
        for _ in range(n):
            t0 = time.perf_counter()
            fn()
            best = min(best, (time.perf_counter() - t0) * 1000)
        return best

    rnn_ms, attn_ms = best_of(rnn_pass), best_of(attn_scores)
    print(f"RNN 逐步循环 {T} 步:        {rnn_ms:7.2f} ms")
    print(f"注意力一次 Q@Kᵀ ({T}×{T}): {attn_ms:7.2f} ms   scores 形状 {tuple(attn_scores().shape)}")
    print(f"→ 本机 CPU 快 {rnn_ms / attn_ms:.0f} 倍。真正的差距在 GPU：矩阵乘法能摊到几千个核上，for 循环永远只能用一个。")


if __name__ == "__main__":
    demo_rnn_decay()
    demo_attention_distance_free()
    demo_serial_vs_parallel()
