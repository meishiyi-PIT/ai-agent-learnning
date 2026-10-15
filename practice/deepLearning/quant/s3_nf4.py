"""
模块六 · 《2.大模型低精度训练与量化实战指南》第 4 章：4bit 与 QLoRA —— 第 3 站
=====================================================================

【4.2 关键洞察：权重是"中间胖、两头瘦"的】（课件 443-460 行）
    把真实大模型某一层线性权重画成直方图，近似零均值的正态分布：绝大多数值挤在 0 附近，越往两头越稀。
    课件用的是 LLaMA2 和 ChatGLM3 的图；本机没有 LLaMA，demo 1 用 Hugging Face 缓存里真实训练过的中文 BERT
    （hfl/rbt3，第 0 层注意力 query 的 768×768 权重）验证同一件事：
        ±1σ / ±2σ / ±3σ 内的比例与标准正态的 68% / 95% / 99.7% 对照；10 桶文本直方图看形状。
    依据：QLoRA 论文（arXiv 2305.14314）第 3 节原话 "pretrained neural network weights usually have a
    zero-centered normal distribution"。真实权重不是严格正态（尖峰、有少量离群值），"近似"两个字要记住。
    demo 2 把 [-absmax, absmax] 等距切成 16 格（INT4 线性量化的做法），数每格里装了多少权重：
        中间两三格挤了绝大多数，两头的格子几乎空着——等距刻度在中间不够用、在两头浪费。
    结论：刻度只有 16 个改不了，那就改切分方式，按"人数"均分（分位数量化），4.3 展开。

【4.3 分位数量化与 NF4】（课件 462-499 行，demo 3）
    分位数量化：把一块权重按"人数"切成 16 组，每组个数一样多，15 个切点叫分位数；每组配一个代表值，
    存"第几组"（4 bit），用时查表还原。中间人挤的地方组窄、分辨率细；两头人少的地方组宽，粗一点无所谓。
    每块现算分位数太贵且小块上抖得厉害。NF4 的招：归一化后权重都像标准正态，就用 N(0,1) 的分位数一次性算好
    一张 16 值的表，所有块共用（表由 bitsandbytes 的 create_normal_map 生成，demo 3 逐位复现）：
        0 附近相邻值隔 0.08，两头 0.723→1.0 隔 0.28，中间比两头密 3.5 倍；负半边 7 个、正半边 8 个 + 精确的 0.0。
    三步（x = [0.42, 0.75, -0.95, 2.71]）：
        ① 块内归一化：除以 absmax 2.71 → [0.155, 0.277, -0.351, 1.0]，落进表的 [-1, 1]；
        ② 最近邻查表：→ 索引 [9, 10, 3, 15]，每个只占 4 bit；
        ③ 反量化：表[索引] × absmax → [0.436, 0.667, -1.070, 2.71]。
    单个向量看不出优势（平均误差 0.055 vs 线性 INT4 的 0.058），NF4 的复利在"亿级参数 × 正态分布"上：
    绝大多数参数落在刻度密集区，整体累计误差被系统性压低。
    工程细节：分块量化 block size = 64，每 64 个参数独立算一个 absmax，离群值只祸害这 64 个数。

运行：
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python quant/s3_nf4.py
    （找不到本地模型时自动退化为 N(0,1) 随机样本示意，输出第一行会标明）
"""

from pathlib import Path

import numpy as np
import torch

HF_HUB = Path.home() / ".cache" / "huggingface" / "hub"
RBT3_SNAPSHOTS = HF_HUB / "models--hfl--rbt3" / "snapshots"
KEY = "bert.encoder.layer.0.attention.self.query.weight"   # 一个普通的 nn.Linear 权重，768×768


def load_real_weight():
    """直接 torch.load 本地缓存里的 state_dict（不需要 transformers），找不到返回 (None, None)"""
    bins = sorted(RBT3_SNAPSHOTS.glob("*/pytorch_model.bin")) if RBT3_SNAPSHOTS.exists() else []
    if not bins:
        return None, None
    state = torch.load(bins[0], map_location="cpu", weights_only=True)
    return state[KEY].float().numpy().ravel(), f"hfl/rbt3 {KEY} {tuple(state[KEY].shape)}"


# ---------- demo 1：真实权重的分布 ----------
w, source = load_real_weight()
if w is None:
    w = np.random.default_rng(0).normal(0.0, 0.04, 768 * 768).astype(np.float32)
    source = "N(0, 0.04) 随机样本【示意，不是真权重】"
print("数据来源:", source, " 个数:", w.size)

mu, sigma = w.mean(), w.std()
print(f"均值 {mu:+.5f}  标准差 {sigma:.5f}  绝对值最大 {np.abs(w).max():.3f}")
for k, ref in ((1, 68.3), (2, 95.4), (3, 99.7)):
    frac = np.mean(np.abs(w - mu) <= k * sigma) * 100
    print(f"  ±{k}σ 内 {frac:5.1f}%   （标准正态 {ref}%）")

edges = np.linspace(mu - 4 * sigma, mu + 4 * sigma, 11)        # ±4σ 切 10 桶
counts, _ = np.histogram(w, bins=edges)
print("10 桶直方图（±4σ 范围）：")
for lo, hi, c in zip(edges[:-1], edges[1:], counts):
    print(f"  [{lo:+.3f}, {hi:+.3f}) {'#' * int(50 * c / counts.max()):50s} {c / w.size * 100:5.1f}%")

# ---------- demo 2：INT4 线性量化的 16 个等距格子各装了多少权重 ----------
absmax = np.abs(w).max()
counts16, _ = np.histogram(w, bins=np.linspace(-absmax, absmax, 17))
pct16 = counts16 / w.size * 100
print(f"\n[-absmax, absmax] 等距切 16 格（每格宽 {2 * absmax / 16:.3f}），各格占比 %：")
print("  " + "  ".join(f"{p:4.1f}" for p in pct16))
print(f"  中间 2 格装了 {pct16[7] + pct16[8]:.1f}%，占比不到 0.1% 的空格子有 {int(np.sum(pct16 < 0.1))} 个")

# ---------- demo 3：NF4 的 16 值表从哪来 + 四个数走一遍三步 ----------
from torch.distributions import Normal


def create_normal_map(offset: float = 0.9677083) -> np.ndarray:
    """复刻 bitsandbytes.functional.create_normal_map(use_extra_value=True)：
    正半边取 N(0,1) 在 [offset, 0.5] 上等距 9 个概率点的分位数（去掉 0.5 那个），负半边取 8 个，再补一个精确的 0，
    排序后除以最大值归一化到 [-1, 1]。offset 是论文/库里定的常数，让两端刚好落在 ±1。"""
    n = Normal(0, 1)
    pos = n.icdf(torch.linspace(offset, 0.5, 9)[:-1]).tolist()        # 8 个正值
    neg = (-n.icdf(torch.linspace(offset, 0.5, 8)[:-1])).tolist()     # 7 个负值
    values = torch.tensor(pos + [0.0] + neg).sort().values
    return (values / values.max()).numpy()


NF4 = create_normal_map()
print("\nNF4 16 值表（由 N(0,1) 分位数生成）：", [round(float(v), 4) for v in NF4])
print(f"  0 附近间隔 {NF4[8] - NF4[7]:.3f}，两头间隔 {NF4[15] - NF4[14]:.3f}，中间比两头密 {(NF4[15] - NF4[14]) / (NF4[8] - NF4[7]):.1f} 倍")

x = np.array([0.42, 0.75, -0.95, 2.71], dtype=np.float32)
absmax_x = np.abs(x).max()                                   # ① 块内归一化的锚点
x_norm = x / absmax_x
idx = np.abs(x_norm[:, None] - NF4[None, :]).argmin(axis=1)  # ② 最近邻：4×16 的距离矩阵，每行取最小的那列
x_deq = NF4[idx] * absmax_x                                  # ③ 查表 × absmax
print("  归一化:", x_norm.round(4), " 索引:", idx.tolist(), " 反量化:", x_deq.round(3))
print("  误差  :", np.abs(x - x_deq).round(3), " 平均", np.abs(x - x_deq).mean().round(4))
q_lin = np.round(x * (7 / absmax_x)); x_lin = q_lin / (7 / absmax_x)      # 对照：4.1 的线性 INT4
print("  线性 INT4 平均误差", np.abs(x - x_lin).mean().round(4))
