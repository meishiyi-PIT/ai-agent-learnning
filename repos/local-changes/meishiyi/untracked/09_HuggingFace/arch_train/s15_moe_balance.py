"""课件 7《图解 MoE 结构》第三部分：负载均衡。

1. 按课件两张图的数字算 CV（变异系数 = 标准差 / 平均值）：偏心时大，均匀时小
2. 用 transformers 里 Qwen3-MoE / Mixtral 真正在用的辅助损失 load_balancing_loss_func（Switch Transformer 版），
   对比"路由均匀"和"路由偏心（几乎都选专家 0）"两种情况，损失差多少
3. 专家容量：课件那句"What is Mixture of Experts ? Summarize"，每个专家最多收 3 个 token，看谁被挤走、谁溢出

运行：cd meishiyi/09_HuggingFace && .venv/Scripts/python -X utf8 arch_train/s15_moe_balance.py
"""
import torch
from transformers.models.qwen3_moe.modeling_qwen3_moe import load_balancing_loss_func

# ---------- 1. CV ----------
for name, imp in [("偏心", [0.8, 0.2, 0.1, 0.05, 0.2]), ("均匀", [0.3, 0.3, 0.2, 0.2, 0.3])]:
    t = torch.tensor(imp)
    print(f"{name}：重要性 {imp} → 标准差 {t.std():.3f} / 平均 {t.mean():.3f} = CV {t.std() / t.mean():.2f}")

# ---------- 2. 辅助损失 = 专家数 × Σ(第 i 个专家分到的 token 比例 × 路由给它的平均概率) ----------
torch.manual_seed(0)
T, E = 1000, 4                                     # 1000 个 token，4 个专家
even = torch.randn(T, E)                           # 路由分数随机 → 大家被选的机会差不多
skew = torch.randn(T, E) + torch.tensor([3.0, 0, 0, 0])   # 专家 0 的分数整体高 3 → 几乎都选它
for name, logits in [("路由均匀", even), ("路由偏心", skew)]:
    share = torch.bincount(logits.argmax(-1), minlength=E) / T
    loss = load_balancing_loss_func((logits,), num_experts=E, top_k=1)
    print(f"{name}：4 个专家各分到的 token 比例 {[round(v, 2) for v in share.tolist()]} → 辅助损失 {loss:.2f}")

# ---------- 3. 专家容量 = 3 ----------
words = ["What", "is", "Mixture", "of", "Experts", "?", "Summarize"]
wish = [[1, 4], [1, 4], [1, 4], [1, 4], [4, 1], [4, 1], [4, 1]]    # 每个 token 的第一、第二志愿（按课件图）
cap, load = 3, {1: 0, 4: 0}
for w, prefs in zip(words, wish):
    got = next((e for e in prefs if load[e] < cap), None)
    if got is None:
        print(f"  {w:10s} 志愿 {prefs} 都满了 → 溢出，这层 MoE 输出 0，只靠残差原样传到下一层")
    else:
        load[got] += 1
        note = "" if got == prefs[0] else f"（第一志愿 FFNN{prefs[0]} 已满）"
        print(f"  {w:10s} → FFNN{got}{note}")
