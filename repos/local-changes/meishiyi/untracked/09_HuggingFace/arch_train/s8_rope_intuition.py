"""追问：RoPE 为什么"转一下"就能表示位置？（完整版在课件 7 RoPE 篇）

最小例子：二维向量当成一根钟表指针。位置 m 的向量逆时针转 m × θ。
注意力打分 = Q·K（点积），两根指针的点积只取决于夹角，
所以打分只和"两个 token 相隔几格"有关，和它们在句子里的绝对位置无关。

运行：cd meishiyi/09_HuggingFace && .venv/Scripts/python -X utf8 arch_train/s8_rope_intuition.py
"""
import math

theta = 0.3                      # 每隔一个位置多转 0.3 弧度（约 17 度）
q = (1.0, 0.0)                   # 某个词的 Query（转之前）
k = (0.6, 0.8)                   # 另一个词的 Key（转之前）


def rotate(v, m):
    a = m * theta
    return (v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a))


def score(q_pos, k_pos):
    rq, rk = rotate(q, q_pos), rotate(k, k_pos)
    return rq[0] * rk[0] + rq[1] * rk[1]


for q_pos, k_pos in [(5, 3), (105, 103), (5, 4)]:
    print(f"Q 在位置 {q_pos:3d}，K 在位置 {k_pos:3d}，相隔 {q_pos - k_pos} 格 → 打分 {score(q_pos, k_pos):.3f}")
