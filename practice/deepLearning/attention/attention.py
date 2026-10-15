"""
模块五 · 《注意力机制》第三节：缩放点积注意力 attention(q, k, v)
==================================================================

【它解决什么问题】
Embedding 查出来的词向量是死的："苹果股价"和"苹果好吃"里的苹果向量一样，`it` 指谁全靠上下文。
注意力让每个词按"和全句其他词的相关度"从其他词那里吸收信息，产出一个**带上下文的新向量**。
相似度只是算相关度的尺子，产出物是新向量。

【Java 视角：模糊版 HashMap】
    map.put(k1, v1); map.put(k2, v2); map.put(k3, v3);
    map.get(q)  普通版：找完全相等的 k，返回它的 v
                注意力：算 q 和每个 k 有多像（点积），把所有 v 按"像的程度"混合返回
    Query = 我在找什么（只用于打分）
    Key   = 我拿什么被找（只用于打分）
    Value = 找到我后拿走什么（只用于混合）

【四行代码 = 四步】（q/k/v 的最后两维是 [seq_len, d]，前面可带 batch、head 维）
    scores = q @ k^T / sqrt(d_k)     ① 打分：每个 q 对每个 k 点积 → [seq_q, seq_k]，再 ② 缩放
    p_attn = softmax(scores, dim=-1)  ③ 每行变成总和为 1 的比例 —— 这排比例就是"注意力"
    return p_attn @ v                 ④ 按比例把 v 加权求和 → [seq_q, d_v]

【为什么 q @ k^T 就是"每个 q 对每个 k 点积"】
    q 是 3 行（3 个词的 q），k 是 3 行（3 个词的 k）。矩阵乘法的定义是"左边每一行 · 右边每一列"，
    所以要把 k 转置（行变列），q @ k^T 的第 i 行第 j 列 = q_i · k_j。一次矩阵乘法把 3×3=9 个点积全算完。
    手算时我们一个词一个词地算，代码里矩阵乘法一次算完全部词 —— 这就是 GPU 快的原因。

【为什么除以 sqrt(d_k)】
    d_k 是 k 向量的长度（有几个数）。点积 = d_k 项相加，d_k 越大分数的绝对值越大。
    分数一大，softmax 就"赢家通吃"：e^30 / (e^30 + e^10) ≈ 1，其余全是 0 —— 比例几乎不随分数变化，
    梯度接近 0，训练不动（CNN 那节笔记讲过的"饱和"）。除以 sqrt(d_k) 把分数压回正常量级。
    d_k=2 时除以 1.41，d_k=512 时除以 22.6。手算例子里为了数字干净没除，代码里必须除。

【softmax 为什么在混合 v 之前】
    softmax 把分数变成"分蛋糕的比例"，比例定好了才知道每个 v 搬多少。先搬再 softmax 没有意义。

【dim=-1 是什么】
    -1 = 最后一维。scores 是 [seq_q, seq_k]，最后一维是"对每个 k 的分数"，
    沿它做 softmax = 每个 q 各自把自己那一排分数变成比例（每行和为 1）。

【和课件手算例子对照】
    demo_hand_calc() 复现"animal / street / it"那个例子：三张表设成单位表（q=k=v=x），
    不除 sqrt(d_k)，结果和纸笔算的 it 新向量 [1.34, 0.53] 一致。demo_scaled() 再看除以 sqrt(d_k) 后的变化。

运行：
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python attention/attention.py
"""

import math

import torch


def attention(q, k, v, dropout=None, scale=True):
    """缩放点积注意力。scale=False 只为复现手算例子，真实使用永远 True。"""
    d_k = k.size(-1)                                       # k 向量的长度

    scores = torch.matmul(q, k.transpose(-2, -1))          # ① 打分 [.., seq_q, seq_k]
    if scale:
        scores = scores / math.sqrt(d_k)                   # ② 缩放

    p_attn = torch.softmax(scores, dim=-1)                 # ③ 每行变比例（和为 1）
    if dropout is not None:
        p_attn = dropout(p_attn)                           # 训练时随机丢一些比例，防过拟合（可选）

    return torch.matmul(p_attn, v), p_attn                 # ④ 加权和；顺便把比例也返回，方便观察


def demo_hand_calc():
    print("=" * 60)
    print("demo 1：复现手算例子（q=k=v=x，不缩放）")
    print("=" * 60)
    # 句子 animal / street / it，词向量 2 个位置 [动物性, 地点性]
    x = torch.tensor([[2.0, 0.0],      # animal
                      [0.0, 2.0],      # street
                      [1.0, 0.5]])     # it
    out, p = attention(x, x, x, scale=False)

    print("scores = q @ k^T（第 i 行 = 第 i 个词的 q 对三个 k 的点积）：")
    print(x @ x.T)
    print("\np_attn = softmax 后的比例（每行和为 1，这排数就是'注意力'）：")
    print(p)
    print("\n新向量 = p_attn @ v：")
    print(out)
    print("\n第 2 行（it）：原来 [1, 0.5] → 新向量", [round(t, 2) for t in out[2].tolist()],
          "  动物性从 1 涨到 1.34，it 从 animal 吸收了内容")
    print("形状：输入", tuple(x.shape), "→ 输出", tuple(out.shape), "（进几行出几行）")


def demo_scaled():
    print("\n" + "=" * 60)
    print("demo 2：为什么要除以 sqrt(d_k)")
    print("=" * 60)
    torch.manual_seed(0)
    for d in (2, 64, 512):
        q = torch.randn(1, d)
        k = torch.randn(5, d)
        raw = q @ k.T
        print(f"d_k={d:3d}  原始分数范围 [{raw.min():6.1f}, {raw.max():6.1f}]"
              f"  softmax 最大比例：不缩放 {torch.softmax(raw, -1).max():.3f}"
              f" / 缩放后 {torch.softmax(raw / math.sqrt(d), -1).max():.3f}")
    print("→ d_k 越大原始分数越大，不缩放时 softmax 被顶成'赢家通吃'（最大比例≈1，其余≈0），梯度接近 0")


def demo_batch_shape():
    print("\n" + "=" * 60)
    print("demo 3：带 batch 维的形状")
    print("=" * 60)
    q = k = v = torch.randn(3, 2, 4)   # batch=3，每句 2 个词，每个向量 4 个数
    out, p = attention(q, k, v)
    print("q/k/v:", tuple(q.shape), "→ 输出", tuple(out.shape), "  p_attn", tuple(p.shape),
          "= [batch, seq_q, seq_k]")


def demo_trace():
    """一行一行打印 attention() 内部每一步的中间结果（"买手机打分"例子）。"""
    print("=" * 60)
    print("demo 0：逐行跟踪 attention() 内部")
    print("=" * 60)
    q = torch.tensor([[2.0, 1.0]])                    # 1 个打分的人：性能权重 2，续航权重 1
    k = torch.tensor([[3.0, 0.0],                     # 手机 A 的指标
                      [0.0, 3.0],                     # 手机 B
                      [1.0, 1.0]])                    # 手机 C
    v = torch.tensor([[10.0, 0.0],                    # 三款手机各自"交出去的内容"
                      [0.0, 10.0],
                      [5.0, 5.0]])
    print("q =", q.tolist(), " 形状", tuple(q.shape))
    print("k =", k.tolist(), " 形状", tuple(k.shape))
    print("v =", v.tolist(), " 形状", tuple(v.shape))

    d_k = k.size(-1)
    print(f"\n[1] d_k = k.size(-1) = {d_k}   ← 每条 k 有几个数（几项指标）")

    raw = q @ k.transpose(-2, -1)
    print(f"[2a] q @ kᵀ = {raw.tolist()}   形状 {tuple(raw.shape)}   ← 每款手机一个总分")
    scores = raw / math.sqrt(d_k)
    print(f"[2b] 除以 sqrt({d_k})={math.sqrt(d_k):.2f} → {[round(s, 2) for s in scores[0].tolist()]}")

    p = torch.softmax(scores, dim=-1)
    print(f"[3] softmax → {[round(s, 3) for s in p[0].tolist()]}   和 = {p.sum().item():.1f}   ← 比例")

    out = p @ v
    print(f"[4] p @ v = {[round(s, 2) for s in out[0].tolist()]}   形状 {tuple(out.shape)}   ← 按比例混合 v")
    print("    = 0.806×[10,0] + 0.097×[0,10] + 0.097×[5,5]")


if __name__ == "__main__":
    demo_trace()
    demo_hand_calc()
    demo_scaled()
    demo_batch_shape()
