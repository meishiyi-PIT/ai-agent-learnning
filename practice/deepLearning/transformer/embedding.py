"""
模块五 · 《5.Transformer》2.1–2.2：Embedding 查表 + 为什么乘 √d_model
====================================================================
（第 2 站 / 共 8 站。上一站：全景架构图。这一站填架构图最上面那格 "Embedding × √d_model"。）

【2.1 Embedding = 一张 (vocab_size, d_model) 的表，用索引取行】
    词向量课件已学：分词 → 每个 token 一个整数索引 → 拿索引去表里取一行。
    nn.Embedding(num_embeddings=词表大小, embedding_dim=d_model) 内部就是这张表（emb.weight），
    随机初始化，训练时和其他参数一样被梯度更新。索引 0 习惯留给 <pad>（填充位）。
    形状：输入 (batch, seq_len) 的整数 → 输出 (batch, seq_len, d_model)。
    Java 视角：float[vocab][d] table; 查词 = table[idx]，一句话 = 按索引挨个取行拼成二维数组。

【先补数学：均值 / 方差 / 标准差，只需要会算这一个例子】
    一组数 [1, 2, 3, 6]
      均值 μ（读 mu）      = (1+2+3+6)/4 = 3                     —— "中心在哪"
      每个数离均值多远     = [-2, -1, 0, 3]
      方差 σ²（读 sigma 方）= (4+1+0+9)/4 = 3.5                  —— "离中心平均有多散"（先平方再平均）
      标准差 σ             = √3.5 ≈ 1.87                          —— 把方差开回原来的单位
    唯一要记住的规律：**一组数整体乘以 c，标准差也乘以 c**。[2, 4, 6, 12] 的 σ = 2 × 1.87 = 3.74。
    "服从 N(0, 1/d)" 读作：一堆数中心在 0、方差 1/d、标准差 1/√d，
    约 68% 的数落在 ±1σ 内、95% 落在 ±2σ 内（正态分布经验法则）。d=512 时 σ = 1/22.6 ≈ 0.044，
    也就是说 95% 的数都挤在 ±0.09 这么窄的范围里。

【2.2 课件的解释：为什么乘 √d_model】
    Xavier 初始化下词向量每个数 ~ N(0, 1/d_model)，标准差 1/√d，太小；
    位置编码（第 3 站）的值域是 [-1, 1]，尺度大得多；两者直接相加，词向量会被位置编码"淹掉"。
    所以先给词向量乘 √d：标准差 (1/√d) × √d = 1，两边站到同一量级再相加。
    手算：d=4 → σ=0.5，×2 → 1.0；d=512 → σ=0.044，×22.6 → 1.0。

【核查：这个解释只在"词表大小 ≈ d_model"时成立，demo 2 有实测】
    xavier_uniform 对一张 (vocab, d) 的表，方差 = 2 / (vocab + d)，不是 1/d：
        vocab=512,  d=512 → σ=0.044, ×√512 → 1.00   课件说法成立
        vocab=10000, d=512 → σ=0.014, ×√512 → 0.31  拉不回 1
        PyTorch 默认初始化（不用 Xavier）σ=1，×√512 → 22.6，反而是词向量把位置编码淹掉
    论文原文没给理由；作者把 Embedding 表和输出层 Linear 共用同一张表（权重绑定），
    Linear 的天然尺度是 1/√d，乘 √d 是为了补这个。课件的说法是流行的"民间解释"，
    记住三点就够：① 它只是一个常数缩放；② 要不要乘取决于表怎么初始化；
    ③ 现代大模型（GPT-2、LLaMA、Qwen）不乘 √d，直接把表初始化成小标准差（GPT-2 用 0.02），
       位置信息也不再用正余弦相加（第 3 站末尾会提）。

【Python 小补】
    emb.weight 是 nn.Parameter（可训练张量）；demo 里手动覆盖它要包在 torch.no_grad() 里，
    否则 PyTorch 会因为"在被追踪梯度的张量上原地改值"报错。
    tensor.std() 直接算标准差；math.sqrt(d) 和 d ** 0.5 一样。

运行：
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python transformer/embedding.py
"""

import math

import torch
from torch import nn


class Embeddings(nn.Module):
    """课件原版：查表 + 乘 √d_model。"""

    def __init__(self, vocab_size: int, d_model: int):
        super().__init__()
        self.lut = nn.Embedding(vocab_size, d_model)   # lut = look-up table，就是那张表
        self.d_model = d_model

    def forward(self, x):
        # x: (batch, seq_len) 整数索引 → (batch, seq_len, d_model)
        return self.lut(x) * math.sqrt(self.d_model)


def demo_lookup():
    print("=" * 64)
    print("demo 1：Embedding 就是按索引取行（把表填成能一眼认出的数）")
    print("=" * 64)
    emb = nn.Embedding(num_embeddings=10, embedding_dim=4)     # 词表 10 个 token，每个 4 维
    with torch.no_grad():
        for i in range(10):
            emb.weight[i] = torch.full((4,), float(i))          # 第 i 行全是 i，方便肉眼核对
    print("表的形状 emb.weight.shape =", tuple(emb.weight.shape), " ← (vocab_size, d_model)")

    two_sentences = torch.tensor([[1, 2, 3],
                                  [4, 5, 0]])                   # 第 2 句只有 2 个词，末尾用 0 填充
    out = emb(two_sentences)
    print("输入 (batch=2, seq_len=3) →", "输出", tuple(out.shape), "← (batch, seq_len, d_model)")
    print(out)
    print("→ 第 1 行取的是表的第 1 行（全 1），第 2 句最后一个位置取的是第 0 行（<pad>）。")


def demo_scale_claim():
    print("\n" + "=" * 64)
    print("demo 2：核查\"Xavier 后词向量 σ=1/√d，乘 √d 拉回 1\" 这个说法")
    print("=" * 64)
    torch.manual_seed(0)
    print(f"{'vocab':>7} {'d':>5} | {'默认init σ':>10} {'×√d 后':>8} | {'Xavier σ':>9} {'×√d 后':>8} | {'1/√d':>6}")
    for vocab, d in [(8, 8), (512, 512), (10000, 512)]:
        e = nn.Embedding(vocab, d)
        s_default = e.weight.std().item()
        nn.init.xavier_uniform_(e.weight)
        s_xavier = e.weight.std().item()
        print(f"{vocab:>7} {d:>5} | {s_default:>10.3f} {s_default * math.sqrt(d):>8.2f} "
              f"| {s_xavier:>9.3f} {s_xavier * math.sqrt(d):>8.2f} | {1 / math.sqrt(d):>6.3f}")
    print("→ 只有 vocab ≈ d 那行 Xavier σ ≈ 1/√d、乘 √d 后 ≈ 1；vocab=10000 时只到 0.31；")
    print("  默认初始化 σ 本来就是 1，乘 √d 后飙到 22.6，反过来把 [-1,1] 的位置编码淹掉。")


def demo_scale_rule():
    print("\n" + "=" * 64)
    print("demo 3：手算规律 —— 一组数整体乘 c，标准差也乘 c")
    print("=" * 64)
    a = torch.tensor([1., 2., 3., 6.])
    print(f"[1,2,3,6]      均值 {a.mean():.2f}  方差 {a.var(unbiased=False):.2f}  标准差 {a.std(unbiased=False):.3f}")
    b = a * 2
    print(f"[2,4,6,12]     均值 {b.mean():.2f}  方差 {b.var(unbiased=False):.2f}  标准差 {b.std(unbiased=False):.3f}  ← 标准差 ×2")
    print("→ 所以 σ=1/√d 的一堆数乘 √d，σ 变成 1。这就是课件 2.2 的全部数学。")


if __name__ == "__main__":
    demo_lookup()
    demo_scale_claim()
    demo_scale_rule()
