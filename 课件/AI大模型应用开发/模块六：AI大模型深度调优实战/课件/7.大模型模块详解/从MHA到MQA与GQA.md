# 注意力机制减负指南：从 MHA 到 MQA 与 GQA
---

## 为什么要在注意力头上动刀？
标准的多头注意力（MHA）里，每个头都有自己独立的一套 Q、K、V 投影。训练阶段这没问题——矩阵一块算，GPU 很 happy。

但到了**自回归解码**阶段，事情就变了：每生成一个新 token，都要把它之前所有 token 的 K、V 从显存里读出来算注意力。为了不重复计算，这些历史 K、V 会缓存在显存里，也就是大名鼎鼎的 **KV Cache**。

问题在于：KV Cache 的大小和「头数」成正比。头越多、序列越长，显存占用越夸张，而且每一步解码都要把这份缓存完整读一遍——**显存带宽**直接成为推理速度的瓶颈。

于是思路就很朴素了：Q 必须保持多样性（它决定每个头"关注什么"），但 K、V 真的需要每个头一份吗？能不能让几个头拼团共用？

### MHA：全员独立的"豪华配置"
H 个头，H 份 Q，H 份 K，H 份 V。表达能力最强，但 KV Cache 里要存 `2 × H` 份矩阵，推理时最烧钱。

<!-- 这是一张图片，ocr 内容为： -->
![在标准的MHA中，每个注意力头都有独立的查询（Q）、键（K）、值（V）矩阵，即： 输入序列通过不同的线性变换生成 H 个独立的 Q、K、V（H 是头数）。 计算复杂度为 O(n^2 * d)（n 是序列长度，d 是模型维度），且需要存储 3 * H 个投影矩阵。 当模型规模增大（如头数 H 增加或序列长度 n 变长）时，计算和内存开销成为瓶颈。](https://cdn.nlark.com/yuque/0/2026/png/21571931/1790164062471-c4cb13b5-6a73-4174-afed-ebbc5b1130d0.png)

### MQA：K/V 只留一份的"极简主义"
<!-- 这是一张图片，ocr 内容为： -->
![](https://cdn.nlark.com/yuque/0/2026/png/21571931/1790164232874-44544a9a-a4a0-4f14-8970-de1d166fc464.png)

核心思想：所有注意力头共享同一个键（K）和值（V）矩阵，仅查询（Q）矩阵保持独立。

实现方式：

生成 H 个不同的 Q 矩阵（每个头一个）。

生成 1 个共享的 K 和 V 矩阵（所有头共用）。

优势：

显著减少 K 和 V 的投影矩阵数量，降低内存占用。

计算量减少（尤其是解码时的自回归生成阶段），因为只需缓存一组 K 和 V。

缺点：

性能可能略低于MHA，因为共享 K/V 限制了模型对不同注意力模式的捕捉能力。

应用场景：推理密集型任务（如大语言模型的生成阶段）

### GQA：拼团式折中（当前主流）
<!-- 这是一张图片，ocr 内容为： -->
![](https://cdn.nlark.com/yuque/0/2026/png/21571931/1790164410080-3a189c37-63d4-4f81-bb99-ee5d5511fcdd.png)

核心思想：介于MHA和MQA之间，将头分成 G 组，每组共享同一个 K 和 V 矩阵。

实现方式：

将 H 个头分为 G 组（例如 G=8，H=64 时每组8个头）。

每组生成独立的 Q 矩阵，但共享同一组 K 和 V。

极端情况下：

当 G=H 时，退化为MHA；

当 G=1 时，退化为MQA。

优势：

平衡计算效率和模型表达能力：通过调整 G，可以灵活控制性能与开销的权衡。

比MQA更接近MHA的性能，同时显著减少计算量。

应用场景：LLaMA-2、GPT-3等模型采用了GQA。

## 算笔账：KV Cache 到底省多少
KV Cache 占用的显存可以这样估算：

$ \text{Bytes} = \text{层数} \times \text{KV头数} \times \text{head\_dim} \times 2 \;(K和V) \times \text{精度字节数} \times \text{序列长度} $

拿一个 7B 级别的典型配置来算（28 层、28 个 Q 头、head_dim=128、FP16、序列长度 1024）：

| 方案 | KV 头数 | KV Cache 大小 | 相对 MHA |
| --- | --- | --- | --- |
| MHA | 28 | ≈ 392 MB | 1× |
| GQA（G=4） | 4 | ≈ 56 MB | **省 86%** |
| MQA | 1 | ≈ 14 MB | 省 96% |


GQA 用 4 个 KV 头就砍掉了八成半的缓存，而质量几乎贴着 MHA——这就是它胜出的原因。 batch 开大、上下文拉长之后，这个差距会被进一步放大。

## 国内模型都在怎么选
+ **Qwen2 / Qwen3 全系**：GQA。比如 Qwen2-7B 是 28 个 Q 头配 4 个 KV 头。
+ **GLM 系列**：同样采用 GQA。

趋势很清楚：**纯 MHA 在新一代大模型里基本绝迹**，大家都在变着法给 KV Cache 瘦身。



## 实战建议
1. **自己训模型**：默认上 GQA，KV 头数取 Q 头数的 1/4 ~ 1/8 是比较稳的甜点位；资源管够再考虑 MHA。
2. **部署推理**：选支持 GQA 感知 kernel 的框架（vLLM、SGLang 都原生支持），否则显式复制 K/V 会把你省下的显存又吃回去。
3. **还想更极致**：去研究下 DeepSeek 的 MLA 思路——低秩压缩 K/V，是目前 KV Cache 瘦身的最前沿打法。

---

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class GroupedQueryAttention(nn.Module):
    def __init__(self, d_model, num_heads, num_groups, dropout=0.1):
        """
        Args:
            d_model: 模型输入/输出的特征维度（例如512）
            num_heads: 注意力头的总数（例如8）
            num_groups: 分组数（必须能被num_heads整除，例如2）
            dropout: 注意力权重的Dropout率
        """
        super().__init__()
        assert d_model % num_heads == 0, "d_model must be divisible by num_heads"
        assert num_heads % num_groups == 0, "num_heads must be divisible by num_groups"
        
        self.d_model = d_model
        self.num_heads = num_heads
        self.num_groups = num_groups
        self.head_dim = d_model // num_heads  # 每个头的维度（例如512/8=64）
        self.group_size = num_heads // num_groups  # 每组包含的头数（例如8/2=4）

        # 1. 定义投影矩阵
        # Q矩阵：保持独立，每个头有自己的投影（输出维度d_model，即num_heads * head_dim）
        self.Wq = nn.Linear(d_model, d_model)
        # K矩阵：分组共享，输出维度为num_groups * head_dim（例如2*64=128）
        self.Wk = nn.Linear(d_model, self.head_dim * num_groups)
        # V矩阵：分组共享，同K
        self.Wv = nn.Linear(d_model, self.head_dim * num_groups)
        # 输出投影矩阵
        self.Wo = nn.Linear(d_model, d_model)

        # Dropout层
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        """
        Args:
            x: 输入序列，形状为 [batch_size, seq_len, d_model]
            mask: 可选，掩码矩阵（如因果掩码），形状为 [batch_size, seq_len, seq_len]
        Returns:
            输出序列，形状与x相同 [batch_size, seq_len, d_model]
        """
        batch_size, seq_len, _ = x.shape

        # ===== 1. 投影Q/K/V =====
        # Q: [batch_size, seq_len, d_model] -> 独立投影到H个头
        Q = self.Wq(x)  
        # K: [batch_size, seq_len, d_model] -> 投影到G组（每组共享）
        K = self.Wk(x)  
        # V: 同K
        V = self.Wv(x)  

        # ===== 2. 调整张量形状以匹配分组 =====
        # Q的形状调整：拆分为num_heads个头
        # [batch_size, seq_len, d_model] -> [batch_size, seq_len, num_heads, head_dim]
        Q = Q.view(batch_size, seq_len, self.num_heads, self.head_dim)
        
        # K/V的形状调整：拆分为num_groups组
        # [batch_size, seq_len, head_dim * num_groups] -> [batch_size, seq_len, num_groups, head_dim]
        K = K.view(batch_size, seq_len, self.num_groups, self.head_dim)
        V = V.view(batch_size, seq_len, self.num_groups, self.head_dim)

        # ===== 3. 广播K/V到所有头（实现分组共享） =====
        # 使用repeat_interleave将K/V从num_groups复制到num_heads
        # 例如：num_groups=2, num_heads=8 -> 每组4个头共享相同的K/V
        # [batch_size, seq_len, num_groups, head_dim] -> [batch_size, seq_len, num_heads, head_dim]
        K = K.repeat_interleave(self.group_size, dim=2)
        V = V.repeat_interleave(self.group_size, dim=2)

        # ===== 4. 计算注意力分数 =====
        # 调整维度顺序以方便矩阵乘法
        # Q: [batch_size, num_heads, seq_len, head_dim]
        Q = Q.transpose(1, 2)
        # K: [batch_size, num_heads, head_dim, seq_len]（需转置最后两维）
        K = K.transpose(1, 2).transpose(-1, -2)
        # V: [batch_size, num_heads, seq_len, head_dim]
        V = V.transpose(1, 2)

        # 计算注意力分数（缩放点积注意力）
        # scores: [batch_size, num_heads, seq_len, seq_len]
        scores = torch.matmul(Q, K) / torch.sqrt(torch.tensor(self.head_dim, dtype=torch.float32))

        # 计算注意力权重
        attn_weights = F.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)  # 可选Dropout

        # ===== 5. 应用注意力权重到V =====
        # output: [batch_size, num_heads, seq_len, head_dim]
        output = torch.matmul(attn_weights, V)

        # ===== 6. 合并所有头并输出 =====
        # 调整维度顺序并合并头
        # [batch_size, seq_len, num_heads, head_dim] -> [batch_size, seq_len, d_model]
        output = output.transpose(1, 2).contiguous()
        output = output.view(batch_size, seq_len, self.d_model)

        # 最终输出投影
        return self.Wo(output)


# 测试代码
if __name__ == "__main__":
    d_model = 512
    num_heads = 8
    num_groups = 2  # 分为2组，每组4个头共享K/V
    batch_size = 2
    seq_len = 10

    # 初始化GQA模块
    gqa = GroupedQueryAttention(d_model, num_heads, num_groups)

    # 模拟输入数据（随机初始化）
    x = torch.randn(batch_size, seq_len, d_model)

    # 前向传播
    output = gqa(x)
    print("输入形状:", x.shape)        # [2, 10, 512]
    print("输出形状:", output.shape)    # [2, 10, 512]（与输入一致）
```

