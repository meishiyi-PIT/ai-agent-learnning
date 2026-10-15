"""
模块六 · 《3.大模型分布式训练实战指南》第一、二章：为什么单卡撑不住 / 三种切法
=====================================================================

【整份课件的地图】（本机 4 站 + 租卡 1 场；🆕 = 新内容）
    1 🆕 第一、二章 两座大山 / 自救手段的天花板 / DP、PP、TP 三种切法        ← 本文件（demo：三种切法下每张卡放多少）
    2 🆕 第三章 数据并行：DataParallel 三坑 + 课件漏掉的 DDP                 dist/s2_ddp_cpu.py
    3 🆕 第四章 流水线并行的气泡 / 张量并行的切矩阵                          dist/s3_tp_split.py
    4 🆕 第五章 DeepSpeed 与 ZeRO 三阶段 / ds_config / TrainingArguments   dist/s4_zero_stages.py
    5 🖥 租卡：单卡 → DDP → ZeRO-2 → ZeRO-3 四组对比                        meishiyi/09_HuggingFace/dist/

【1.1 两座大山 —— 显存这座你已经算过】
    LoRA 第 1 站的四笔账：fp32 训练每个参数 16 字节（权重 4 + 梯度 4 + m 4 + v 4）。
    课件的 10B 例子：10B × 16 = 160 GB，还不含激活值；最大的单卡 80 GB，装不下。
    第二座山是算力：GPT-3 量级单卡要跑几十年，不是省一省能解决的，只能把计算摊到成百上千张卡。

【1.2 / 1.3 自救手段和它们的天花板】
    问：LoRA 已经把梯度和优化器状态两笔账省掉了，为什么还不够？
    答：①权重那笔省不掉 —— 基座必须完整地在显存里。LoRA 只解决"微调"的账。
    问：那 QLoRA 把权重压到 4bit，不就把①也省了？
    答：微调可以，预训练不行 —— 预训练要全参数、全精度地更新，量化会丢精度。
    结论：从头训练、或全参数微调一个单卡装不下的模型 → 只剩分布式一条路。

【2 三种切法 —— 问题只有一个：怎么切】
    DP 数据并行：模型复制 N 份，数据切 N 份。每张卡都要装下整个模型；卡间只同步梯度。
    PP 流水线并行：模型按层切 N 段，每卡一段，数据像流水线依次经过。卡间只传 stage 边界的激活值，通信量小。
    TP 张量并行：一层内部的权重矩阵按行/列切 N 块，每卡算一块再拼。每层前向反向都要通信，必须同机 NVLink。
    问：三种切法哪一种不省显存？
    答：DP。它只提速不省显存，每张卡还是一整份模型 —— 所以课件说"装得下就 DP，装不下才切模型"。
    问：超大模型为什么三样一起上（3D 并行）？
    答：TP 通信最频繁放节点内（NVLink），PP 通信最少可以跨节点，DP 包最外层把拼好的整套再复制几份来吃数据。

demo 1 = 课件 1.1 那张表（10B 模型 fp32 训练四项各占多少）；demo 2 = 第二章三种切法下每张卡放多少。

运行：
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python dist/s1_three_ways.py
"""

CARD_GB = 80                # 一张 A100 / H800 的显存

# 课件 1.1 表格的四行：名字 → 每个参数占几字节（fp32 = 4 字节；Adam 的 m、v 各一份所以是 8）
FP32_ACCOUNTS = {
    "模型参数": 4,
    "梯度": 4,
    "优化器状态（Adam 的 m + v）": 8,
}
BYTES_PER_PARAM_FP32 = sum(FP32_ACCOUNTS.values())   # 4 + 4 + 8 = 16，和 LoRA 第 1 站 demo 1 算出来的一样


def demo_1_1_memory_mountain():
    print("=" * 64)
    print("demo 1：课件 1.1 第一座山 —— 10B 参数、fp32 训练，显存四项各占多少")
    print("=" * 64)
    params = 10e9   # 10B = 100 亿个参数；1e9 是 Python 科学计数法 = 10 的 9 次方，结果是 float
    total = 0
    for name, bytes_per_param in FP32_ACCOUNTS.items():   # dict.items() 一次拿 键 和 值 两个
        gb = params * bytes_per_param / 1e9
        total += gb
        print(f"  {name:<18}{gb:5.0f} GB   ← {bytes_per_param} 字节 × 10B")   # :<18 左对齐宽 18；:5.0f 宽 5 不带小数
    print(f"  {'合计':<18}{total:5.0f} GB   ← 每参数 {BYTES_PER_PARAM_FP32} 字节，还没算激活值")
    print(f"  最大的单卡 {CARD_GB} GB → 装不下，差 {total / CARD_GB:.0f} 倍")
    print()


def per_card_gb(params: float, n_cards: int, how: str) -> float:
    """params 个参数，切到 n_cards 张卡，按 how 切，每张卡要放多少 GB（不含激活值）。"""
    total = params * BYTES_PER_PARAM_FP32 / 1e9
    if how == "DP":
        return total            # 复制：每张卡一整份，卡再多也不变
    return total / n_cards      # PP / TP：切模型，每张卡只放 1/N


def demo_2_three_ways():
    print("=" * 64)
    print("demo 2：课件第二章 —— 同一个 10B 模型、4 张 80 GB 卡，三种切法下每张卡放多少")
    print("=" * 64)
    params, n = 10e9, 4
    # 列表里每个元素是 (切法, 说明) 二元组，for 直接拆开成两个变量
    for how, note in [("DP", "复制模型、切数据：每卡一整份，装不下就没法用"),
                      ("PP", "按层切：每卡 1/N 的层"),
                      ("TP", "切每一层：每卡 1/N 的权重")]:
        gb = per_card_gb(params, n, how)
        fits = "装得下" if gb <= CARD_GB else "装不下"   # 条件表达式：Java 的 cond ? a : b
        print(f"  {how} ×{n} 卡：每卡 {gb:6.0f} GB  {fits}  {note}")
    print()
    small = per_card_gb(0.5e9, 1, "DP")
    print(f"  换 Qwen2.5-0.5B：0.5B × 16 字节 = {small:.0f} GB < {CARD_GB} GB → 直接 DP，4 张卡各跑一整份，只为吃数据快 4 倍")


if __name__ == "__main__":
    demo_1_1_memory_mountain()
    demo_2_three_ways()
