"""
模块六 · 《1.大模型LoRA微调》第三章：LoRA 原理深度拆解 —— 亲手写一个 LoRA 层
==========================================================================

本站分四小块：3a 公式与参数账（demo 1）→ 3b 初始化的玄机（demo 2）→ 3c 低秩假设与边界（demo 3）→ 3d 合并 / 分离两种用法（demo 4）
3.5 "挂在哪些层"没有单独 demo（要有 Transformer 才能演示，第 4 站用真模型看），讲解在下面。

【3a 核心公式，一行】
        W' = W + ΔW = W + (α/r) · B · A
    W：预训练权重，冻结，一个数都不改。课件写 d×d；一般是 d_out × d_in（第 2 站的 m×n）。
    B：d_out × r，可训练；A：r × d_in，可训练；r：秩，一般 4~64，远小于 d_out 和 d_in。
    B·A：就是第 2 站 2c 的"(m×r)·(r×n)" —— 一个秩 ≤ r 的增量矩阵 ΔW。
    α/r：缩放因子。α 是超参数（常取 2r，此时缩放 = 2）。为什么除以 r：
        B·A 的每个格子是 r 项之和，r 越大这个和的量级越大；除以 r 之后换 r 时增量的量级大致不变，
        学习率等超参不用跟着重调（论文原话：scaling by α/r reduces the need to retune hyperparameters when varying r）。
        课件 4.4 提到的 rsLoRA 是把 α/r 改成 α/√r（PEFT 里 use_rslora=True）。
    前向传播，输入 x 走两条路再相加：
        h = W x + (α/r) · B (A x)
        原路 W x 保留老本事；旁路先 A x（d_in → r，"降维"），再 B(·)（r → d_out，"升维"），学新任务的增量。
        计算顺序先 A 后 B：中间结果只有 r 维，便宜。
    类比：全量微调是整栋楼拆了重装；LoRA 是主体不动，在关键位置加几个可调节装置。

【3.2 参数账 —— demo 1 亲手数】
    一个 4096×4096 的权重：全量 16,777,216 个参数要更新；LoRA r=8：B 4096×8 + A 8×4096 = 65,536，占 0.39%。
    整个模型（通常给注意力层的 Q、V 都挂上）：可训练参数占原模型 0.1%~1%。
    第 1 站的四笔账在 LoRA 下：①权重 全量加载（省不掉）；②梯度 只给 A、B 存；③优化器状态 只给 A、B 存；④激活值 基本不变。
    课件"7B 全量 60GB / LoRA 23GB"是量级估计（第 1 站勘误④）。

【3b 初始化的玄机 —— demo 2 三种方案对比】
    论文方案：A 用小的随机高斯值，B 置零。训练一开始 B·A = 0，旁路输出为 0，模型和原模型逐比特一致；
        LoRA 分支从零开始平滑地"长"出能力，不会一上来用随机噪声污染模型。
    两种作死方案：
        A、B 都置零：∂L/∂B 正比于 A（=0），∂L/∂A 正比于 B（=0），两个梯度互相锁死，永远学不动（demo 2 看梯度范数全 0、loss 纹丝不动）。
        A、B 都随机：起点 B·A 是个不小的随机矩阵，模型还没训就先被"打了一拳"（demo 2 看初始输出被扰动了多少）。
            注意 demo 2 的小玩具上 both_random 最终也收敛了 —— 它演示的是"起点被污染"，不是"学不会"；
            真模型上这一拳意味着先把预训练能力打乱再学回来，收敛慢甚至翻车。
    细节（demo 2 第 0 步能看到）：论文方案在第 0 步 A 的梯度也是 0（因为 B=0，h 暂时不依赖 A），
        但 B 的梯度不为 0（正比于 A x）；走一步 B 非零后 A 才开始动 —— 这就是"A 随机提供对称性破缺"的意思。
    勘误③：PEFT 库默认对 A 用 kaiming_uniform（和 nn.Linear 默认一样）、B 置零（peft 0.15.2 tuners/lora/layer.py:185-193）；
        `init_lora_weights="gaussian"` 才是论文的高斯（std = 1/r）。结论一样：起点 B·A = 0。

【3c 低秩假设与边界 —— demo 3】
    LoRA 赌的是"微调需要的权重变化 ΔW 是低秩的"。demo 3 造两种目标：
        目标 1：真实增量是秩 2 的矩阵 → r=8 的 LoRA 几百步就把 loss 压到几乎 0；
        目标 2：真实增量是随机满秩矩阵 → r=8 的 LoRA 只能抹掉一小部分 loss，r 加到 64 好一些但仍差得远。
    这就是课件 3.6 的第一条边界：任务和预训练差异极大、需要的变化真是高秩时，LoRA 表达力不够，老实全量微调。
    其余边界：擅长调"行为"不擅长灌"知识"（知识找 RAG）；r 和 target_modules 要在评测集上试；数据不行神仙难救。

【3d 训练完的两种用法 —— demo 4】
    合并（Merge）：W_new = W + (α/r)·B·A，把增量加回原矩阵。合并后结构、参数量、推理速度和原模型完全一样，零额外延迟。上线部署用。
    分离（Adapter）：A、B 单独存成小文件（几 MB 到几百 MB），推理时动态加载；一个基座挂 N 个 LoRA，热切换。多任务用。
    demo 4 验证：合并前后同一输入输出逐元素相同；同一基座换两套 (A,B) 输出不同、基座权重没动。

【3.5 挂在哪些层（讲解，无 demo）】
    Transformer 每层两类密集矩阵：注意力的 Q、K、V、O 四个投影；FFN 的升维/降维（Qwen/DeepSeek 叫 gate_proj / up_proj / down_proj）。
    论文（arXiv 2106.09685，Table 5 / Table 6）实验结论：
        预算有限时同时挂 Wq 和 Wv 性价比最高；r=4、8 已够（Wq+Wv 上 r=1 都能打）；
        给更多矩阵挂 LoRA 常比把单一矩阵的 r 调大更划算。
    PEFT 的 target_modules 写法：经济型 ["q_proj","v_proj"]；标准型加 k_proj、o_proj；豪华型再加 gate_proj/up_proj/down_proj。
    每个矩阵的 LoRA 参数 = (输入维 + 输出维) × r；第 4 站迷你模型（hidden 64、kv 32、r=8、2 层）：
        q 1024 + k 768 + v 768 + o 1024 = 3584/层 × 2 = 7168，和 get_peft_model 后打印的可训练参数一致。
    课件没说的现代补充：QLoRA 论文（Dettmers 2023，arXiv 2305.14314）在 LLaMA-7B 上发现只挂 q、v 追不上全量微调，
        所有线性层都挂才能追平、r 反而影响不大；PEFT 为此提供 target_modules="all-linear"。
        现在的做法：显存够就全挂（豪华型），显存紧才从 q+v 起步。
    嵌入层（参数多、变动小）、LayerNorm（参数极少）、bias 默认都不碰。

运行：
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python lora/s3_lora_by_hand.py
"""

import math

import torch
from torch import nn


class LoRALinear(nn.Module):
    """h = W x + (α/r) · B (A x)。W 冻结；A: r×d_in，B: d_out×r。"""

    def __init__(self, base: nn.Linear, r: int, alpha: float, init: str = "paper"):
        super().__init__()
        self.base = base
        for p in self.base.parameters():   # 冻结原权重：第 1 站 demo 2 的套路
            p.requires_grad_(False)
        d_out, d_in = base.weight.shape
        self.r = r
        self.scale = alpha / r
        self.A = nn.Parameter(torch.empty(r, d_in))
        self.B = nn.Parameter(torch.empty(d_out, r))
        if init == "paper":            # 论文：A 高斯、B 置零
            nn.init.normal_(self.A, std=0.02)
            nn.init.zeros_(self.B)
        elif init == "both_zero":      # 作死 1
            nn.init.zeros_(self.A)
            nn.init.zeros_(self.B)
        elif init == "both_random":    # 作死 2：两个都按 nn.Linear 默认初始化
            nn.init.kaiming_uniform_(self.A, a=math.sqrt(5))
            nn.init.kaiming_uniform_(self.B, a=math.sqrt(5))
        else:
            raise ValueError(init)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, d_in)。先 A 后 B：x @ Aᵀ 得 (batch, r)，再 @ Bᵀ 得 (batch, d_out)
        return self.base(x) + self.scale * (x @ self.A.T @ self.B.T)

    def delta_w(self) -> torch.Tensor:
        return self.scale * (self.B @ self.A)          # ΔW = (α/r)·B·A，形状 d_out×d_in

    def merged_linear(self) -> nn.Linear:
        """3d：把增量加回原矩阵，返回一个和原模型结构完全一样的 nn.Linear。"""
        lin = nn.Linear(self.base.in_features, self.base.out_features, bias=self.base.bias is not None)
        with torch.no_grad():
            lin.weight.copy_(self.base.weight + self.delta_w())
            if self.base.bias is not None:
                lin.bias.copy_(self.base.bias)
        return lin


def n_trainable(m: nn.Module) -> int:
    return sum(p.numel() for p in m.parameters() if p.requires_grad)


def n_all(m: nn.Module) -> int:
    return sum(p.numel() for p in m.parameters())


def train(lora: LoRALinear, target_fn, steps: int, lr: float = 5e-3, seed: int = 0):
    """用 (x, target_fn(x)) 训练 LoRA 的 A、B；返回 (训练前 loss, 训练后 loss)，两者都在同一批固定的评估数据上算。"""
    torch.manual_seed(seed)
    x_eval = torch.randn(256, lora.base.in_features)
    eval_loss = lambda: (lora(x_eval) - target_fn(x_eval)).pow(2).mean().item()
    opt = torch.optim.Adam([p for p in lora.parameters() if p.requires_grad], lr=lr)
    with torch.no_grad():
        before = eval_loss()
    for _ in range(steps):
        x = torch.randn(64, lora.base.in_features)     # 每步一批新数据：学的是函数，不是背样本
        loss = (lora(x) - target_fn(x)).pow(2).mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
    with torch.no_grad():
        after = eval_loss()
    return before, after


def demo_formula_and_param_account():
    print("=" * 64)
    print("demo 1（3a）：公式、形状、参数账")
    print("=" * 64)
    torch.manual_seed(0)
    base = nn.Linear(4096, 4096, bias=False)
    lora = LoRALinear(base, r=8, alpha=16)
    print(f"  W {tuple(base.weight.shape)} 冻结；A {tuple(lora.A.shape)}；B {tuple(lora.B.shape)}；缩放 α/r = {lora.scale}")
    print(f"  可训练 {n_trainable(lora):,} / 总 {n_all(lora):,} = {100 * n_trainable(lora) / n_all(lora):.2f}%")
    x = torch.randn(4, 4096)
    diff = (lora(x) - base(x)).abs().max().item()
    print(f"  初始化后（B=0）：LoRA 输出 vs 原输出 最大差 = {diff}  ← 逐比特一致，模型还是原模型")
    mid = x @ lora.A.T
    print(f"  旁路中间结果 A x 形状 {tuple(mid.shape)}：4096 维先压到 r={lora.r} 维，再升回 4096")
    print()


def demo_init_schemes():
    print("=" * 64)
    print("demo 2（3b）：三种初始化方案（d=256, r=8, α=16）")
    print("=" * 64)
    d = 256
    torch.manual_seed(0)
    base = nn.Linear(d, d, bias=False)
    delta = torch.randn(d, 2) @ torch.randn(2, d) * 0.05      # 真实增量：秩 2
    target = lambda x: base(x) + x @ delta.T
    x0 = torch.randn(64, d)

    for init in ("paper", "both_zero", "both_random"):
        torch.manual_seed(1)
        lora = LoRALinear(base, r=8, alpha=16, init=init)
        perturb = (lora(x0) - base(x0)).norm() / base(x0).norm()
        loss = (lora(x0) - target(x0)).pow(2).mean()
        loss.backward()
        gA0, gB0 = lora.A.grad.norm().item(), lora.B.grad.norm().item()
        first, last = train(lora, target, steps=200)
        print(f"  [{init:>11}] 初始输出被扰动 {100 * perturb:.1f}%  | 第 0 步梯度范数 A={gA0:.4f} B={gB0:.4f}  | loss {first:.5f} → 200 步后 {last:.5f}")
    print("  读法：paper 起点零扰动、B 先动 A 后动、loss 降到几乎 0；both_zero 梯度全 0、loss 纹丝不动；")
    print("        both_random 起点先挨一拳（输出偏离原模型一倍多）。这个小玩具最后也能收敛，")
    print("        但真模型上这一拳 = 先把预训练能力打乱再慢慢学回来，收敛慢甚至翻车 —— 课件 3.3 的意思。")
    print()


def demo_low_rank_assumption():
    print("=" * 64)
    print("demo 3（3c）：真实增量低秩 vs 满秩，LoRA 能学到多少（d=256）")
    print("=" * 64)
    d = 256
    torch.manual_seed(0)
    base = nn.Linear(d, d, bias=False)
    low = torch.randn(d, 2) @ torch.randn(2, d)
    full = torch.randn(d, d)
    full = full * (low.norm() / full.norm())        # 两种增量总能量（范数）一样大，只差秩
    print(f"  秩 2 增量的秩 = {int(torch.linalg.matrix_rank(low))}，满秩增量的秩 = {int(torch.linalg.matrix_rank(full))}，范数都是 {low.norm():.1f}")
    for name, delta in (("秩 2 增量", low), ("满秩增量", full)):
        target = lambda x, delta=delta: base(x) + x @ delta.T * 0.05
        for r in (8, 64):
            torch.manual_seed(1)
            lora = LoRALinear(base, r=r, alpha=2 * r)
            first, last = train(lora, target, steps=400)
            print(f"  {name}  r={r:2d}：loss {first:.4f} → {last:.4f}（剩 {100 * last / first:.1f}%），可训练 {n_trainable(lora):,}")
    print("  读法：低秩目标 r=8 几乎学完；满秩目标 r=8 只抹掉一小截，r=64 好一些但离 0 很远 —— 3.6 第一条边界。")
    print()


def demo_merge_and_adapter():
    print("=" * 64)
    print("demo 4（3d）：合并回原权重 / 保持分离热切换（d=256）")
    print("=" * 64)
    d = 256
    torch.manual_seed(0)
    base = nn.Linear(d, d, bias=False)
    w_before = base.weight.clone()
    adapters = {}
    for name, seed in (("客服", 10), ("法务", 20)):
        torch.manual_seed(seed)
        delta = torch.randn(d, 2) @ torch.randn(2, d) * 0.05
        lora = LoRALinear(base, r=8, alpha=16)
        train(lora, lambda x, delta=delta: base(x) + x @ delta.T, steps=300)
        adapters[name] = lora

    x = torch.randn(4, d)
    lora = adapters["客服"]
    merged = lora.merged_linear()
    print(f"  合并：W_new = W + (α/r)·B·A → 新层参数 {n_all(merged):,} 个 = 原层 {n_all(base):,} 个，结构一样")
    print(f"        合并前后同一输入输出最大差 = {(merged(x) - lora(x)).abs().max().item():.2e}  ← 零额外延迟的依据")
    print(f"  分离：同一基座挂两套 (A,B)：客服 vs 法务 输出最大差 = {(adapters['客服'](x) - adapters['法务'](x)).abs().max().item():.3f}")
    print(f"        基座权重是否被改动：{not torch.equal(base.weight, w_before) and '改了' or '没动'}")
    a_bytes = sum(p.numel() for p in (lora.A, lora.B)) * 4
    print(f"        一套 adapter 文件大小 ≈ {a_bytes / 1024:.0f} KB（d=256）；4096 维 r=8 ≈ {65536 * 4 / 1024:.0f} KB/层")
    print()


if __name__ == "__main__":
    demo_formula_and_param_account()
    demo_init_schemes()
    demo_low_rank_assumption()
    demo_merge_and_adapter()
