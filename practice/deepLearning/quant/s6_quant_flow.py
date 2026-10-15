"""
【量化到底发生在哪一步：把"推理 INT8"和"训练 QLoRA"两条线各手动回放一遍】—— 第 6 站
配合 C:\\workspace\\code\\lora\\quant_demo.py（int8 模式）和 lora_train_fixed.py（USE_4BIT=1）讲解。纯标准库。
看点：标签 ① 的量化只在加载时做一次；② ③ 都是每次乘法前后的临时转换，存在显存里的 W 从来没被改过。

推理这条线（quant_demo.py int8）
磁盘 safetensors（BF16）                         ← 从头到尾不变
   │ from_pretrained(..., load_in_8bit=True)
   ▼
① 加载：每个线性层的 W  BF16 → INT8（逐行，做一次，16 位原件丢掉）
         Embedding / lm_head / norm 不量化，16 位放进显存
   ▼
显存：线性层 = INT8 + 每行 absmax ｜ 其余 = 16 位    ← 之后一直这样
   │ generate() 循环，每圈写一个 token
   ▼
每圈：Embedding 查表（16 位）
      → 28 层，每层的每个线性层做三步：
           ② 输入 x：16 位 → INT8（临时，也按行）
              INT8(x) × INT8(W) → 大整数
           ③ 大整数 × 两边 absmax ÷ 127 ÷ 127 → 16 位小数，交给下一层
              （W 一直是 INT8，没人碰它）
      → lm_head（16 位）给 15 万个词打分 → 取最高分 → 下一个 token

nf4 推理只改 ②：不压 x，而是把 W 临时解压成 16 位再正常相乘；③ 因此也不需要了。

训练这条线（lora_train_fixed.py，USE_4BIT=1 即 QLoRA）
磁盘（BF16）
   │ from_pretrained(..., load_in_4bit=True)                lora_train_fixed.py:63-73
   ▼
① 加载：线性层 W  BF16 → NF4（每 64 个一块，做一次）；Embedding / lm_head 16 位
   │ prepare_model_for_kbit_training：全部冻结、没量化的层升 FP32、开梯度检查点
   │ get_peft_model：在 target_modules 指定的线性层旁边长出 A、B（FP32，可训练）
   │   lora_train_fixed.py:130 只挂 q/k/v/o_proj 四个注意力层，MLP 的 gate/up/down_proj 没有旁路；
   │   quant_demo.py nf4 模式的演示才是 7 种线性层全挂
   ▼
显存：W = NF4（冻结）｜ A、B = FP32 ｜ Embedding / lm_head = FP32
   │ 训练循环，每一步：
   ▼
前向：每个线性层   ② W：NF4 → BF16（临时解压）→ W·x
                   A、B：FP32 → BF16 → B·(A·x)
                   两路相加 → 下一层 …… → lm_head → 和标准答案比 → loss
反向：只算 A、B 的梯度（路过 W 时再临时解压一次，用完丢；W 没有梯度）
更新：优化器只改 A、B（FP32）。W 一个字节没动
   ▼
保存：只存 A、B（adapter，几十 MB）                        lora_train_fixed.py:175
   ▼
merge.py：重新按 BF16 读磁盘原件 + B·A 加进 W → 存成新的 BF16 模型   merge.py:27-31
          → 部署时可以再走上面"推理"那条线（加载时 INT8 或 4bit）

不用量化的训练（全参 / 普通 LoRA）：这两条线上一个 ① 都没有。普通 LoRA（USE_4BIT=0）：W 按 BF16 读进来、冻结、就以 BF16 存；
只有 A、B 是 FP32 存、BF16 算（peft 自动把 A/B 升成 FP32）。全参：按什么精度加载就以什么精度存和更新——BF16 加载 + bf16=True 时
Trainer 只把前向包进 autocast，W 和优化器状态都是 BF16，没有 FP32 主副本；只有 FP32 加载 + bf16=True 才是课件说的"BF16 算、FP32 存"。
训练里量化只出现在 QLoRA 的冻结基座上；被更新的数（全参的 W、LoRA 的 A/B）从不量化。本仓库的训练不用 INT8
（peft 也支持在 INT8 冻结基座上挂 LoRA；bnb 的 8bit 优化器压的是优化器状态、不是权重）。

两条细节，地图里为了简洁省掉了（bitsandbytes 0.50.2 / transformers 4.51.3 源码核对过）：
- 没传 torch_dtype 时，真实链路是 BF16 → FP16 → INT8/NF4：transformers 先把读进来的张量统一成 FP16，bitsandbytes 再压。
- INT8 的 ② 还有离群列分解：x 里出现 |值|≥6 的那几列不压，留 16 位单独和对应的 W 列（临时解压）相乘，结果加回去；显存里的 INT8 W 照样没被改。
- NF4 逐 token 生成时（每步输入只有 1 行）用融合内核边读边解压，不落一份完整的 16 位 W；一次算整段提示词或训练时才整层解压后普通矩阵乘。

本脚本 PART B 把 2×2 的表当一整块（真实块大小 64），所以 W1 小数值的那一行 [0.05, 0.02] 被压成编号 7（= 0.0）、0.83 变 0.918——
这是块太大、离群值拖累邻居的真实写照，也是 64 一块 + 双重量化存在的理由。step 1 里 A 的梯度是 0，因为 LoRA 的 B 初始为 0（标准做法），B 动了之后 A 才有梯度。

运行：
    cd C:\\workspace\\deepLearning\\quant
    python -X utf8 s6_quant_flow.py
"""

# ---------- 玩具模型：磁盘上的 BF16 原件（本脚本里从头到尾不改这几张表） ----------
EMB = [[1.0, 0.5], [-0.5, 1.0], [0.2, -0.8]]      # Embedding：3 个 token × 2 维
W1 = [[0.83, -1.27], [0.05, 0.02]]                 # 线性层 1：行0 数值大，行1 数值小
W2 = [[2.56, -3.18], [-0.04, 0.01]]                # 线性层 2
LM_HEAD = [[-1.0, 0.0], [1.0, 0.0], [0.0, 1.0]]    # lm_head：给 3 个候选 token 打分
# NF4 的 16 个刻度（bitsandbytes create_normal_map 的结果，s3_nf4.py 复现过，这里取 4 位小数）
NF4 = [-1.0, -0.6962, -0.5251, -0.3949, -0.2844, -0.1848, -0.0910, 0.0,
       0.0796, 0.1609, 0.2461, 0.3379, 0.4407, 0.5626, 0.7230, 1.0]


def fmt(nums, nd=3):
    """一组数按 nd 位小数拼成字符串，只为打印好看。"""
    return "[" + ", ".join(f"{v:.{nd}f}" for v in nums) + "]"


def fmt2(table, nd=3):
    """2 行的小表打印成 [[..], [..]]。"""
    return "[" + ", ".join(fmt(row, nd) for row in table) + "]"


def matvec(W, x):
    """W·x：每一行和 x 逐个相乘再相加。"""
    return [sum(w * v for w, v in zip(row, x)) for row in W]


def quantize_row(row):
    """INT8 逐行量化（同 s5）：整数 = round(x * 127 / absmax)。返回 (整数列表, absmax)。"""
    absmax = max(abs(v) for v in row)
    return [round(v * 127 / absmax) for v in row], absmax


def nearest_code(v):
    """v 在 [-1, 1] 之间，找 NF4 表里离它最近的那个刻度，返回编号 0~15。"""
    best = 0
    for k in range(16):
        if abs(v - NF4[k]) < abs(v - NF4[best]):
            best = k
    return best


def nf4_quantize_block(values):
    """一块数 → (编号列表, 块 absmax)：先除以 absmax 归一化，再最近邻查表。"""
    absmax = max(abs(v) for v in values)
    return [nearest_code(v / absmax) for v in values], absmax


def nf4_dequant(codes, absmax):
    """编号 → 小数：查表 × absmax。"""
    return [NF4[k] * absmax for k in codes]


# =============== PART A  推理 INT8（quant_demo.py int8） ===============
print("=" * 60)
print("PART A  推理 INT8（quant_demo.py int8）")
print(f"[磁盘] BF16 原件，从头到尾不变: W1={fmt2(W1, 2)}  W2={fmt2(W2, 2)}")
print(f"       EMB={fmt2(EMB, 1)}  LM_HEAD 3×2")
print("[加载①] 线性层 BF16 → INT8（逐行，只做一次）:")
Q = {}                                              # 显存里的线性层：每行 (整数, absmax)
for name, W in (("W1", W1), ("W2", W2)):
    Q[name] = [quantize_row(row) for row in W]
    print(f"   {name}: " + " | ".join(f"行{i} {ints} absmax {am}" for i, (ints, am) in enumerate(Q[name])))
print("   16 位原件丢掉；Embedding / lm_head 不量化，16 位放进显存")


def int8_linear(name, W, x):
    """一个线性层的三步：② 压 x → 整数乘 → ③ 还原成小数。W 只用于算精确值做对照。"""
    ints_x, am_x = quantize_row(x)                                        # ② 临时压 x
    bigs = [sum(a * b for a, b in zip(ints_x, ints_w)) for ints_w, _ in Q[name]]   # 整数乘
    out = [big * am_x * am_w / 127 / 127 for big, (_, am_w) in zip(bigs, Q[name])]  # ③ 还原
    exact = matvec(W, x)
    err = max(abs(a - b) for a, b in zip(out, exact))
    print(f"   {name} ② x→INT8 {ints_x} absmax_x {am_x:.3f}   整数乘 INT8(x)·INT8(W) = {bigs}")
    print(f"      ③ 整数×absmax_x×absmax_W÷127÷127 → {fmt(out)}   精确 W·x {fmt(exact)}   误差 {err:.3f}")
    return out
# 真实 LLM.int8() 还会把 |x|>6 的离群列单独用 FP16 算再加回来（混合精度分解），这里省略。


ids = [0]                                           # 起始 token
for k in range(1, 4):
    x = EMB[ids[-1]]
    print(f"[第{k}圈] token {ids[-1]} → Embedding 查表 x={fmt(x)}（16 位）")
    for name, W in (("W1", W1), ("W2", W2)):
        x = int8_linear(name, W, x)
    scores = matvec(LM_HEAD, x)
    ids.append(scores.index(max(scores)))
    print(f"   W 仍是 INT8；lm_head（16 位）打分 {fmt(scores)} → 最高分 → token {ids[-1]}  序列 {ids}")

# =============== PART B  训练 QLoRA（lora_train_fixed.py USE_4BIT=1） ===============
print("=" * 60)
print("PART B  训练 QLoRA（lora_train_fixed.py USE_4BIT=1）")
NF = {}                                             # 显存里的 W：(编号, 块 absmax)，整张 2×2 当一块（真实 64 个一块）
for name, W in (("W1", W1), ("W2", W2)):
    NF[name] = nf4_quantize_block(W[0] + W[1])
    print(f"[加载①] {name} BF16 → NF4: 编号 {NF[name][0]}  块 absmax {NF[name][1]}")
print("   Embedding / lm_head 不量化")
print("[prepare] 全部冻结 / 没量化的层升 FP32 / 开梯度检查点")
P = {"A1": [0.1, -0.1], "B1": [0.0, 0.0], "A2": [0.05, 0.1], "B2": [0.0, 0.0]}   # r=1：A 是 1×2，B 是 2×1
LAYERS = (("W1", "A1", "B1"), ("W2", "A2", "B2"))
print("[get_peft_model] 每层旁边长出 A(1×2)、B(2×1)，r=1，B 初始为 0；A、B 是 FP32，可训练")


def forward(x, show=False):
    """两层前向：每层 = ② 临时解压 W 算 W·x  +  旁路 B·(A·x)。"""
    for wname, aname, bname in LAYERS:
        vals = nf4_dequant(*NF[wname])                       # ② NF4 → 小数（临时，用完丢）
        Wd = [vals[0:2], vals[2:4]]
        main = matvec(Wd, x)
        A, B = P[aname], P[bname]
        s = A[0] * x[0] + A[1] * x[1]                        # A·x（一个数）
        side = [B[0] * s, B[1] * s]                          # B·(A·x)
        x = [m + d for m, d in zip(main, side)]
        if show:
            print(f"   {wname} ② NF4→小数 {fmt2(Wd)}  W·x {fmt(main)} + B·(A·x) {fmt(side)} → {fmt(x)}")
    return x


def loss_of(x, t):
    return sum((o - v) ** 2 for o, v in zip(forward(x), t))


X, T, LR, H = [1.0, 0.5], [1.0, -1.0], 0.1, 1e-4
for step in (1, 2):
    print(f"[训练 step {step}] 前向 x={fmt(X, 1)}  目标 t={fmt(T, 1)}")
    forward(X, show=True)
    base = loss_of(X, T)
    print(f"   loss = {base:.3f}")
    grads = {}
    for key in P:                                            # 反向：只对 A、B 用"挪一点看 loss 变多少"估梯度
        grads[key] = []
        for i in range(2):
            old = P[key][i]
            P[key][i] = old + H
            grads[key].append((loss_of(X, T) - base) / H)
            P[key][i] = old
    print("   反向：W 没有梯度（冻结）；A、B 的梯度 " + "  ".join(f"{k}{fmt(g, 2)}" for k, g in grads.items()))
    for key in P:                                            # 更新：只改 A、B
        for i in range(2):
            P[key][i] -= LR * grads[key][i]
    print(f"   更新(lr={LR})：只改 A、B；W 的 NF4 编号没变，W1 仍是 {NF['W1'][0]}")

print("[保存] 只存 A、B（adapter）；NF4 的 W 不保存: " + "  ".join(f"{k}{fmt(v)}" for k, v in P.items()))
print(f"[merge] 重新按 BF16 读磁盘原件 W1 = {fmt2(W1, 2)}")
BA = [[P["B1"][i] * P["A1"][j] for j in range(2)] for i in range(2)]      # B·A 是 2×2（真实还乘 α/r）
W1_new = [[W1[i][j] + BA[i][j] for j in range(2)] for i in range(2)]
print(f"        W1_new = W1 + B1·A1 = {fmt2(W1_new)} → 存成新的 BF16 模型（新文件；磁盘原件不动）")
