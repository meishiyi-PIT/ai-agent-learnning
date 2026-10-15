"""
模块六 · 《1.大模型LoRA微调》第一章：微调这件事 —— 从全量微调到 PEFT
=====================================================================

【整份课件的地图】（5 站；🆕 = 新内容，📺 = 录播）
    1 🆕 第一章 为什么要微调 / 三条路线 / 全量微调三座大山 / PEFT 家族       ← 本文件（demo：显存四笔账）
    2 🆕 第二章 数学地基：秩 / 低秩分解（纯数学，不谈模型）                    lora/s2_rank.py
    3 🆕 第三章 LoRA 原理：公式 / 参数账 / 初始化 / 合并 / 挂哪些层 / 边界      lora/s3_lora_by_hand.py
    4 🆕 第四章 工程实战：PEFT + Trainer 真代码走读 + 课件代码勘误             meishiyi/09_HuggingFace/lora/
    5 📺 录播 1_Lora微调/Lora微调_01、_02 验证补漏

【1.1 模型已经很强，为什么还要微调】
    模型"会" ≠ "稳定地按你的要求会"。课件三个例子全是同一类问题：
        固定 JSON 结构 / 行业腔调话术 / 分类抽取的判断标准统一 —— 都是"风格、格式、判断标准"。
    提示词能管一时管不了稳定，这时才轮到微调。
    定义一句话：拿特定领域的数据集，对已经预训练好的模型接着训，让它在特定任务上表现更好。

【1.2 三条路线口诀（这句要背）】
        提示词 解决 临时要求；RAG 解决 外部知识；微调 解决 稳定行为。
    典型误用：把"让模型知道公司最新产品价格"拿去微调 —— 知识会过时，这是 RAG 的活，微调了也白干。
    （对号入座：模块三 Agentic_Rag 项目 = RAG 路线；本模块 = 微调路线。）

【1.3 全量微调三座大山 —— demo 1 亲手算第一座】
    第一座 显存：训练时显存里同时放四样东西 ——
        ①权重  ②梯度  ③优化器状态  ④激活值（前向传播的中间结果，反向传播要用）
    Java 视角：模型的每个 float 参数背后，训练时还各挂着 3 个一样大的 float 数组：
        grad（这次算出来往哪改）、m（AdamW 的一阶动量：历史梯度的滑动平均）、v（二阶动量：历史梯度平方的滑动平均）。
        —— m、v 就是模块五学过的 Adam 优化器"记住的历史"，一个参数记两份。
    fp32 下每个参数：4（权重）+ 4（梯度）+ 4（m）+ 4（v）= 16 字节，不含激活值。
        7B 模型 × 16 字节 = 112 GB。课件写"60GB 以上"，对应的是全部用 bf16（每参数约 8 字节 = 56GB）的省内存配置，
        量级一致：随便哪种算法，一张 24GB 的 4090 都塞不下 7B 全量微调。
    第二座 存储：全量微调一个任务产出一份完整模型副本（7B ≈ 十几 GB），十个任务一百多 GB。
    第三座 风险：所有参数都在动，原有通用能力可能被冲掉（"灾难性遗忘"）；数据差、学习率大就"学歪"。

【1.4 PEFT 家族的共同思路 —— demo 2】
    PEFT = Parameter-Efficient Fine-Tuning，参数高效微调。全家一句话：
        冻结原模型绝大部分参数，只训一小撮（或新增少量）参数，用极低成本逼近全量微调。
    "冻结"在代码里就是 requires_grad=False：这个参数不再产生梯度，优化器也不再给它分配 m/v ——
        四笔账里的②③对这些参数直接消失；只剩①权重（省不掉，基座总得在显存里）和④激活值。
    demo 2 用家族里最简单的成员 BitFit（只训 bias）演示这个账；
    课件那张七行表里，最终赢家是 LoRA：效果接近全量、实现简单、训练完能合并回原权重所以推理零延迟、生态最好。
    第 3 站亲手写一个 LoRA；第 2 站先把它名字里的"低秩"讲明白。

运行：
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python lora/s1_memory.py
"""

import torch
from torch import nn

MB = 1024 ** 2


def mb(numel: int, bytes_per_param: int = 4) -> float:
    """numel 个参数、每个占 bytes_per_param 字节，折合多少 MB。"""
    return numel * bytes_per_param / MB


def demo_full_finetune_accounts():
    print("=" * 64)
    print("demo 1：全量微调的显存四笔账（一个 4096×4096 的权重矩阵）")
    print("=" * 64)
    torch.manual_seed(0)
    layer = nn.Linear(4096, 4096, bias=True)
    w = layer.weight
    n = w.numel()
    print(f"权重 W 形状 {tuple(w.shape)}，参数个数 {n:,}，fp32 占 {mb(n):.0f} MB")
    print(f"  训练前：W.grad = {w.grad}，优化器状态 = 空")

    opt = torch.optim.AdamW(layer.parameters(), lr=1e-3)
    x = torch.randn(4, 4096)  # batch=4 的输入
    h = layer(x)              # ④激活值：一个中间结果，反向传播要用它
    loss = h.pow(2).mean()
    loss.backward()           # 产生 ②梯度
    opt.step()                # 产生 ③优化器状态（AdamW 的 m / v）

    st = opt.state[w]
    print(f"  backward 后：W.grad 形状 {tuple(w.grad.shape)}，占 {mb(w.grad.numel()):.0f} MB")
    print(f"  step 后：优化器给 W 存了 {sorted(st.keys())}")
    print(f"      exp_avg(m) 占 {mb(st['exp_avg'].numel()):.0f} MB，exp_avg_sq(v) 占 {mb(st['exp_avg_sq'].numel()):.0f} MB")
    print(f"  ①+②+③ = {4 * mb(n):.0f} MB = 权重的 4 倍 → 每个参数 16 字节（不含激活值）")
    print(f"  ④激活值 h 形状 {tuple(h.shape)}，这里只占 {mb(h.numel()):.3f} MB ——")
    print("     小是因为只有 1 层、batch=4、序列长度 1；真模型是 几十层 × batch × 序列长度 × 隐藏维，随 batch 和序列长度线性涨。")
    print()
    print("  按 16 字节/参数（fp32）和 8 字节/参数（全 bf16）估算整模型的 ①②③：")
    for name, params in [("Qwen2.5-0.5B", 0.5e9), ("1.5B", 1.5e9), ("7B", 7e9)]:
        print(f"    {name:>13}：{params * 16 / 1e9:6.0f} GB（fp32）   {params * 8 / 1e9:5.0f} GB（bf16）")
    print("  一张 RTX 4090 = 24 GB。")
    print()


def demo_freeze_removes_two_accounts():
    print("=" * 64)
    print("demo 2：PEFT 的共同思路 —— 冻结之后，梯度和优化器状态两笔账消失")
    print("=" * 64)
    torch.manual_seed(0)
    layer = nn.Linear(4096, 4096, bias=True)
    layer.weight.requires_grad_(False)   # 冻结大矩阵（1677 万个参数）
    # BitFit：只训 bias（4096 个参数）—— PEFT 家族里最简单的成员，够用来演示"账"怎么变
    trainable = [p for p in layer.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(trainable, lr=1e-3)

    x = torch.randn(4, 4096)
    loss = layer(x).pow(2).mean()
    loss.backward()
    opt.step()

    print(f"  W.grad = {layer.weight.grad}   ← 冻结的参数没有梯度（不是 0，是根本没分配这块内存）")
    print(f"  bias.grad 形状 = {tuple(layer.bias.grad.shape)}")
    print(f"  优化器里有状态的参数个数 = {len(opt.state)}（只有 bias）")
    n_all = sum(p.numel() for p in layer.parameters())
    n_tr = sum(p.numel() for p in trainable)
    print(f"  可训练 {n_tr:,} / 总 {n_all:,} = {100 * n_tr / n_all:.3f}%")
    print(f"  ①权重仍要 {mb(n_all):.0f} MB（基座得在）；②+③ 从 {mb(2 * n_all):.0f} MB 降到 {mb(2 * n_tr):.3f} MB")
    print("  PEFT 家族的账全是这个套路：省②③，①省不掉（想省①要靠量化 —— 第 2 篇课件 QLoRA 的事）。")
    print()


if __name__ == "__main__":
    demo_full_finetune_accounts()
    demo_freeze_removes_two_accounts()
