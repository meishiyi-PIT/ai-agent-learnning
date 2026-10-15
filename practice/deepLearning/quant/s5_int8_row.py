"""
【INT8 逐行量化：拿一张 2 行 × 4 列的权重小表，手算一遍 bitsandbytes 加载时做的事】—— 第 5 站
配合 C:\\workspace\\code\\lora\\quant_demo.py 的 int8 模式讲解（python quant_demo.py int8，
即 from_pretrained(..., quantization_config=BitsAndBytesConfig(load_in_8bit=True))）。纯标准库，不装任何第三方包。

1. INT8 = 1 字节，只能装 -127~127 这些整数，装不下 0.83 这种小数。
2. 所以每一行先定一把"尺子"：unit = 该行 absmax / 127（把"米"换成"厘米"，小数就能记成整数）。
3. 存的是 整数 + 这把尺子；用的时候 整数 × unit 还原（有取整误差，回不到原值）。
4. 每行各自一把尺子（row-wise），因为不同行数值大小差几十倍，全表共用一把尺子会把小数值行磨平（见第 4 段）。
5. 这件事只在 from_pretrained 加载时做一次：bitsandbytes 把每个 nn.Linear 的权重换成 INT8 整数 + 每行一个 absmax。

运行：
    cd C:\\workspace\\deepLearning\\quant
    python -X utf8 s5_int8_row.py
"""

# ---------- 原始权重表：2 行 × 4 列 ----------
row0 = [0.83, -1.27, 2.56, -3.18]   # 数值"大"的一行（绝对值最大 3.18）
row1 = [0.05, 0.02, -0.04, 0.01]    # 数值"小"的一行（绝对值最大 0.05，比上一行小 60 多倍）
table = [row0, row1]


def fmt(nums, nd=3):
    """把一组数按 nd 位小数拼成字符串，只为打印好看。"""
    return "[" + ", ".join(f"{x:.{nd}f}" for x in nums) + "]"


def quantize_row(row, absmax=None):
    """absmax 逐行量化。absmax 不传就用本行自己的；传进来则表示"强行共用别人的尺子"（第 4 段用）。"""
    if absmax is None:
        absmax = max(abs(x) for x in row)          # 本行绝对值最大的那个数，当锚点
    unit = absmax / 127                            # 一格整数代表多大的浮点值（尺子的最小刻度）
    ints = [round(x * 127 / absmax) for x in row]  # 浮点 → 整数：除以刻度再四舍五入，落在 -127~127
    restored = [q * absmax / 127 for q in ints]    # 整数 → 浮点：整数 × 刻度（反量化）
    max_err = max(abs(x - r) for x, r in zip(row, restored))
    return absmax, unit, ints, restored, max_err


# ---------- 1. 原始表 ----------
print("=" * 60)
print("1. 原始权重表（BF16：每个数 2 字节，8 个数 = 16 字节）")
for i, row in enumerate(table):
    print(f"   row{i} = {fmt(row, 2)}")

# ---------- 2. 逐行量化 ----------
print("=" * 60)
print("2. 逐行 absmax INT8 量化（每行各自一把尺子）")
for i, row in enumerate(table):
    absmax, unit, ints, restored, max_err = quantize_row(row)
    print(f"   row{i}:")
    print(f"     absmax      = {absmax}")
    print(f"     unit        = absmax / 127 = {unit:#.5g}   （1 格整数 = 这么大的浮点值）")
    print(f"     整数        = round(x * 127 / absmax) = {ints}")
    print(f"     还原        = 整数 * absmax / 127     = {fmt(restored)}")
    print(f"     本行最大误差 = {max_err:.6f}")

# ---------- 3. 量化后占多少空间 ----------
print("=" * 60)
print("3. 量化后存储：8 个整数 × 1 字节 = 8 字节  +  2 个 absmax（每行 1 个）")
print("   （真实模型一行有 3584 个数，每行多存 1 个 absmax 几乎不占地方；这张 2×4 小表只是为了看清过程）")

# ---------- 4. 反例：全表共用一把尺子 ----------
print("=" * 60)
print("4. 反例：如果整张表共用一把尺子（absmax 取全表最大 3.18）")
absmax_all = 3.18
absmax, unit, ints, restored, max_err = quantize_row(row1, absmax=absmax_all)
print(f"   row1 用 3.18 当 absmax：unit = {unit:#.5g}")
print(f"     整数        = round(x * 127 / 3.18) = {ints}")
print(f"     还原        = {fmt(restored)}      （原值 {fmt(row1, 2)}）")
print(f"     本行最大误差 = {max_err:.6f}   ← 比逐行量化时大了几十倍")
print("   0.01 被记成 0（整个丢掉），0.02 被记成 0.025；一行只剩 0、±1、±2 几个刻度可用。")
print("   所以 bitsandbytes 每行各配一个 absmax（row-wise），小数值的行才不会被大数值的行拖垮。")
