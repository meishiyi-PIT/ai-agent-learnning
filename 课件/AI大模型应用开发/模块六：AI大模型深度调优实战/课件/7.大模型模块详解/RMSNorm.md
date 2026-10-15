# RMSNorm
---

## 先从 LayerNorm 说起
Transformer 里归一化层的作用不用多讲：把每一层的输入分布稳住，让训练不崩。LayerNorm（LN）对单个 token 的特征向量做两件事——**先减均值（re-centering），再除以标准差（re-scaling）**：

<!-- 这是一张图片，ocr 内容为： -->
![](https://cdn.nlark.com/yuque/0/2026/png/21571931/1790157378138-a488f630-bc52-496e-8046-aaa2e9f68724.png)

这套流程在大模型时代有个不爽的地方：**计算步骤偏多**。一次均值、一次方差、减均值、再除标准差——对每一层每一个 token 都要来一遍。在几百亿参数的模型里，归一化层被调用的次数极其恐怖，蚊子腿也是肉，积少成多就是实打实的训练开销。

## RMSNorm 的思路：均值那步，不要了
<!-- 这是一张图片，ocr 内容为： -->
![](https://cdn.nlark.com/yuque/0/2026/png/21571931/1790157332891-35c2425e-8934-4f85-a2ee-542020671377.png)

RMSNorm（Root Mean Square Layer Normalization）的作者观察到一个现象：LayerNorm 起作用的关键其实是**缩放（re-scaling）**，而不是**中心化（re-centering）**。既然如此，干脆把减均值整步砍掉，只用均方根（RMS）来做缩放：

<!-- 这是一张图片，ocr 内容为： -->
![](https://cdn.nlark.com/yuque/0/2026/png/21571931/1790157352126-e5341bec-0cf7-4cbb-bdb2-61648d3883ba.png)

变化一目了然：

<!-- 这是一张图片，ocr 内容为： -->
![](https://cdn.nlark.com/yuque/0/2026/png/21571931/1790163900077-1aaf0726-389a-47c8-bee9-914190cc1690.png)

省掉了均值统计、减均值操作，连可学习的平移参数 $ \beta $ 也一并省了。原论文报告在不同任务和模型规模上能拿到 **7% ~ 64%** 的提速，而精度和 LayerNorm 基本持平。

## 为什么砍掉均值还能 work？
直觉上可以这样理解：

1. **真正防炸的是缩放。** 深层网络里数值爆炸主要来自特征量级失控，除以 RMS 直接把向量的模长归一到一个稳定范围，梯度就稳了。
2. **中心化是隐式完成的。** 后续的线性层自带偏置、残差连接也在不断混合信息，"均值不为零"这件事并不会累积成灾难——实践证明了这一点。
3. **少一次统计，少一次同步。** 在分布式训练里，归一化的统计量计算往往牵涉通信，步骤越少越友好。

当然，这不是说 RMSNorm 全面碾压 LN——个别对均值敏感的任务上 LN 仍有优势。但对主流 LLM 架构而言，RMSNorm 是性价比之王。

## 手写一个 RMSNorm（PyTorch）
```python
import torch
import torch.nn as nn


class RMSNorm(nn.Module):
    """均方根层归一化

    与 LayerNorm 的区别：不计算均值、不做中心化，
    只用特征的均方根值做缩放，再乘一个可学习的增益 γ。
    """

    def __init__(self, dim: int, eps: float = 1e-6):
        """
        Args:
            dim: 特征维度（即每个 token 向量的长度，例如 4096）
            eps: 防止除零的小常数，1e-6 是 LLaMA 同款默认值
        """
        super().__init__()
        self.eps = eps
        # 可学习的缩放参数 γ，初始化为 1（即开局时等价于纯归一化，不做额外缩放）
        self.weight = nn.Parameter(torch.ones(dim))

    def _norm(self, x: torch.Tensor) -> torch.Tensor:
        """核心归一化逻辑：x / RMS(x)"""
        # x.pow(2).mean(-1)：沿特征维算平方的均值，即均方（Mean Square）
        # torch.rsqrt：一步到位算 1/sqrt(.)，比先 sqrt 再取倒数更快、数值更稳
        # keepdim=True 保持维度以便广播：[B, T, dim] -> [B, T, 1]
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # 先转 float32 再归一化：FP16/BF16 下平方和容易溢出或精度不足，
        # 这是工业界实现的标准做法（LLaMA、Qwen 的源码里都这么写），
        # 算完再转回输入的原始 dtype
        output = self._norm(x.float()).type_as(x)
        return self.weight * output


if __name__ == "__main__":
    x = torch.randn(2, 128, 4096, dtype=torch.bfloat16)  # 模拟 BF16 训练场景
    rms_norm = RMSNorm(4096)
    out = rms_norm(x)
    print("输出形状:", out.shape)   # torch.Size([2, 128, 4096])
    print("输出 dtype:", out.dtype)  # torch.bfloat16（与输入一致）
```

## 小结
| 维度 | LayerNorm | RMSNorm |
| --- | --- | --- |
| 统计量 | 均值 + 方差 | 仅均方根 |
| 可学习参数 | γ、β | 仅 γ |
| 计算步骤 | 多 | 少（提速 7%~64%） |
| 效果 | 基准 | 基本持平 |
| 生态 | 老牌通用 | LLM 事实标准（Qwen/DeepSeek/LLaMA） |


<!-- 这是一张图片，ocr 内容为： -->
![](https://cdn.nlark.com/yuque/0/2026/png/21571931/1790163974335-bfcff48e-83ea-4e79-8139-1f9047692c80.png)

