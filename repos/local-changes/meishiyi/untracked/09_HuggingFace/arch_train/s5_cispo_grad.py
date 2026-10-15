"""追问：CISPO 说"裁剪只限制幅度、但保留梯度"，是怎么做到的？

只拿一个 token 算账：它在采样时概率 0.10，更新几步后涨到 0.15，
优势 A = +1（这条回答比组内平均好，应该鼓励）。
对照 MiniMind trainer/train_grpo.py 里 loss_type 分支的两行：

  grpo : -min(ratio*A, clamp(ratio, 1-eps, 1+eps)*A)
  cispo: -(clamp(ratio, max=eps_high).detach() * A * logp)

看 loss 对 logp 的梯度：grpo 被裁成常数 → 梯度 0；cispo 权重冻结成数字、梯度走 logp → 非 0。
（这里 eps_high 取 1.2 方便和 grpo 对比；MiniMind 默认是 5.0）

运行：cd meishiyi/09_HuggingFace && .venv/Scripts/python -X utf8 arch_train/s5_cispo_grad.py
"""
import math

import torch

old_logp = math.log(0.10)   # 采样时的概率（旧策略，常数）
A = 1.0                     # 优势
eps, eps_high = 0.2, 1.2

for loss_type in ["grpo", "cispo"]:
    logp = torch.tensor(math.log(0.15), requires_grad=True)   # 当前概率，可训练
    ratio = torch.exp(logp - old_logp)                        # 0.15 / 0.10 = 1.5
    if loss_type == "cispo":
        w = torch.clamp(ratio, max=eps_high).detach()         # 1.2，只是个数字
        loss = -(w * A * logp)
    else:
        loss = -torch.min(ratio * A, torch.clamp(ratio, 1 - eps, 1 + eps) * A)
    loss.backward()
    print(f"{loss_type:5s}  ratio={ratio.item():.2f}  loss={loss.item():+.3f}  梯度={logp.grad.item():+.3f}")
