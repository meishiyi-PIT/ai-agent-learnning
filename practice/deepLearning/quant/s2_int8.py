"""
模块六 · 《2.大模型低精度训练与量化实战指南》第 3 章：INT8 量化 —— 第 2 站
=====================================================================

【3.1 什么是量化】
    把浮点数乘一个缩放系数、四舍五入成 INT8 的 256 个整数刻度之一（-128~127），用时再除回去。
    和"12.34 元存成 1234 分"一回事，只是系数不固定，按数据自己定。收益：显存、带宽等比例省；代价：取整误差。

【3.2 absmax 线性量化】（课件 324-351 行的代码，原样收在 demo 1）
    三步：absmax 当锚点 → scale = 127 / absmax → q = round(x × scale)；反量化 x' = q / scale。
    锚点对 127 不对 128：正负对称，0 永远精确落在 0 上（对称量化）。存 q 和 scale 两样。
    x = [0.83, -1.27, 2.56, -3.18] → q = [33, -51, 102, -127]，误差 0.004 左右，个位数量级的权重可忽略。
    scale 以完整 FP32 存，课件的两位小数只是显示；误差的大头永远是取整，不是 scale 的小数位。

【3.3 量化误差：离群值】（demo 2）
    x = [35, 38, 42, 280]：一个 280 把 scale 撑到 127/280 = 0.45，相邻两个刻度之间隔 1/0.45 = 2.2，
    三个正常值被挤进 16、17、19 这几个刻度，分辨率从 demo 1 的 0.025 变成 2.2，粗了 88 倍。
    Transformer 隐层激活里总有少数几个维度比别人大几十倍（论文叫 emergent features），
    误差逐层累积，模型性能肉眼可见地崩——这就是 INT8 不能直接用在大模型上的原因，3.4 的 LLM.int8() 专治它。

【3.4 LLM.int8()：离群值走 VIP 通道】（demo 3）
    矩阵乘 Y = X·W 里，X 的离群值总集中在少数几个固定的列（隐层维度）上。三个动作：
      分解：按阈值（默认 6.0）把 X 里含离群值的列挑出来，W 里对应的行也挑出来，拆成"离群小矩阵"和"正常大矩阵"；
      分治：正常部分走 INT8 矩阵乘（X 每行一个 scale、W 每列一个 scale，叫 vector-wise），离群部分走 FP16 矩阵乘；
      合并：INT8 结果反量化后与 FP16 结果相加，得到 FP16 输出。
    demo 3 用一行 [0.5, -1.2, 40.0, 0.8] 演示：不拆时 40 把刻度撑到 0.315，0.5 被记成 0.63；
    把 40 拆走后正常部分刻度 0.0094，0.5 记成 0.5008。离群列只占约 0.1%，FP16 那条路的开销可忽略。
    课件写"13B 以内精度持平"是低估：论文（Dettmers 2022，arXiv 2208.07339）到 OPT-175B 都零退化，
    这套分解正是为 6.7B 以上才出现的涌现离群特征设计的。

运行：
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python quant/s2_int8.py
"""

import numpy as np


def absmax_quantize(x: np.ndarray):
    """absmax 对称量化：把浮点向量压成 INT8。x: np.ndarray 是类型提示，只给人看，Python 不检查。"""
    absmax = np.abs(x).max()                  # 第 1 步：逐元素取绝对值 → 再取最大 → 得到一个数（锚点）
    scale = 127.0 / absmax                    # 第 2 步：缩放系数，反量化要靠它还原，必须存下来
    q = np.round(x * scale).astype(np.int8)   # 第 3 步：标量 × 数组 = 每个元素都乘；round 取整；astype 转成 1 字节整数
    return q, scale                           # 返回一个元组，调用方用 q, scale = ... 拆开


def absmax_dequantize(q: np.ndarray, scale: float):
    """反量化：整数除回缩放系数，还原成浮点（有精度损失，回不到原值）"""
    return q.astype(np.float32) / scale       # 先转回浮点再除，避免整数除法的歧义


# ---------- demo 1：课件 3.2 的四个数 ----------
x = np.array([0.83, -1.27, 2.56, -3.18], dtype=np.float32)   # 列表 → 数组，显式指定 4 字节浮点
q, scale = absmax_quantize(x)
x_recovered = absmax_dequantize(q, scale)
print("scale   :", scale)
print("量化结果:", q)
print("反量化  :", x_recovered.round(4))
print("误差    :", np.abs(x - x_recovered).round(4))
print()

# ---------- demo 2：课件 3.3 的离群值例子（某创业团队月薪，千元） ----------
x2 = np.array([35, 38, 42, 280], dtype=np.float32)
q2, scale2 = absmax_quantize(x2)
x2_recovered = absmax_dequantize(q2, scale2)
print("scale   :", scale2, " 相邻刻度间隔 = 1/scale =", round(1 / scale2, 2))
print("量化结果:", q2)
print("反量化  :", x2_recovered.round(2))
print("误差    :", np.abs(x2 - x2_recovered).round(2))
print()

# ---------- demo 3：LLM.int8() 的分解思想，一行隐状态 ----------
x3 = np.array([0.5, -1.2, 40.0, 0.8], dtype=np.float32)
threshold = 6.0
is_outlier = np.abs(x3) >= threshold                       # 布尔数组 [False False True False]，标出离群列
q_all, s_all = absmax_quantize(x3)                          # 不拆：整行一起量化
q_norm, s_norm = absmax_quantize(x3[~is_outlier])           # 拆：~ 取反，只量化正常列
print("不拆 刻度间隔", round(1 / s_all, 4), " 0.5 →", absmax_dequantize(q_all, s_all).round(4)[0])
print("拆后 刻度间隔", round(1 / s_norm, 4), " 0.5 →", absmax_dequantize(q_norm, s_norm).round(4)[0],
      " 离群列 40.0 走 FP16 原样保留")
