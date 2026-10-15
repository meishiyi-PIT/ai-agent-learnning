"""
模块五 · 第 5 块：nn.Embedding —— 一张可以被训练的查找表
================================================================

【本块要解决的问题】
第 1~4 块把路铺到了这里：文本 → 分词 → 每个 token 拿到一个整数 ID。
但神经网络吃的是浮点数张量，不是整数 ID。
「整数 ID → 浮点向量」这一步谁来做？答案就是 nn.Embedding。

--------------------------------------------------------------------
一、纯定义（先不管神经网络，就当成一个数据结构）
--------------------------------------------------------------------
nn.Embedding(V, D) 内部只有一样东西：一个 V 行 D 列的浮点数矩阵 W。

它支持的唯一操作是：给一个整数 i（0 <= i < V），把 W 的第 i 行原样还给你。

    Embedding(i) = W[i]        # W[i] 是一个长度为 D 的向量

就这么多。没有加法、没有激活函数、没有任何计算。
V 叫 num_embeddings（有多少行 = 词表能装多少个不同 token），
D 叫 embedding_dim（每行多长 = 每个 token 用几个数表示）。

--------------------------------------------------------------------
二、直觉（Java 视角）
--------------------------------------------------------------------
    float[][] W = new float[V][D];   // 构造时随机填满
    float[] out = W[i];              // 这就是 Embedding 的全部

唯一的区别是：W 里的每个数都是**可训练参数**。
普通 Java 数组里的数是你写死的；W 里的数会被反向传播一点点改掉。
所以"训练词向量"不是什么神秘操作 —— 就是让这张表里的数字自己挪位置，
挪到"语义相近的词，行向量也相近"为止。

再说一遍这个关键反直觉点：
**Embedding 层不是把词"算"成向量的，它是把向量"查"出来的。**
词向量不是某个函数的输出，它本身就是模型的权重，和 Linear 层的 weight 平级。

--------------------------------------------------------------------
三、手算算例（拿纸笔就能验证，下面 demo_1 会跑出同样的数）
--------------------------------------------------------------------
设 V=4, D=3，权重矩阵 W 是：

           d0    d1    d2
    行0 [ 0.0   0.1   0.2 ]
    行1 [ 1.0   1.1   1.2 ]
    行2 [ 2.0   2.1   2.2 ]
    行3 [ 3.0   3.1   3.2 ]

输入 tensor([2, 0, 3])，输出就是把第 2、0、3 行按顺序摞起来：

    [[ 2.0  2.1  2.2 ]
     [ 0.0  0.1  0.2 ]
     [ 3.0  3.1  3.2 ]]

形状：输入 (3,) → 输出 (3, 3)，也就是 (3, D)。

★ 形状规则（唯一需要背的一条）：
    输入形状是什么，输出就在**最后面追加一个 D 维**。
        (L,)      -> (L, D)
        (B, L)    -> (B, L, D)
        (B, L, K) -> (B, L, K, D)
    Embedding 从不改变前面那些维度，它只负责"每个整数长胖成 D 个数"。

--------------------------------------------------------------------
四、为什么它等价于 one-hot 矩阵乘法（这一段是理解的关键）
--------------------------------------------------------------------
第 3 块说过 one-hot 又高又稀。那 one-hot 和 Embedding 到底什么关系？
答案：**数学上完全等价，工程上差了几千倍**。

把索引 2 写成 one-hot 行向量（V=4）：h = [0, 0, 1, 0]
用它左乘 W（1×4 的行向量 乘 4×3 的矩阵 = 1×3 的行向量），逐个算：

    结果[d0] = 0*0.0 + 0*1.0 + 1*2.0 + 0*3.0 = 2.0
    结果[d1] = 0*0.1 + 0*1.1 + 1*2.1 + 0*3.1 = 2.1
    结果[d2] = 0*0.2 + 0*1.2 + 1*2.2 + 0*3.2 = 2.2

得到 [2.0, 2.1, 2.2]，正是 W 的第 2 行。

看清楚发生了什么：one-hot 里那 3 个 0 把 W 的其余 3 行全乘没了，
只有那个唯一的 1 把第 2 行原样放行。所以 **one-hot 乘矩阵 = 按行号取行**。

于是：
  · 数学上   Embedding 就是 one-hot @ W，它能反向传播、能被优化器更新，
             和一个没有 bias 的 Linear 层没有任何本质区别。
  · 工程上   词表 5 万时，one-hot @ W 要做 5 万次乘法，其中 49999 次在乘 0；
             Embedding 直接按下标取行，0 次乘法。省掉的正是那 99.998% 的无用功。

这也是第 3 块那句"one-hot 发身份证、词向量发性格画像"的底层解释：
one-hot 从来没有真的消失，它只是被"取下标"这个动作吸收掉了。

--------------------------------------------------------------------
五、padding_idx 是干嘛的
--------------------------------------------------------------------
一个 batch 里的句子长短不一（"今天天气不错" 6 个词，"好" 1 个词），
但张量必须是规整的矩形，所以短句要用一个特殊 token <pad> 补齐到同样长度。
<pad> 通常占索引 0。

问题来了：<pad> 是我们硬塞进去的假词，它凭什么也去学一个词向量？
padding_idx=0 就是告诉 PyTorch：

    1. 构造时把第 0 行初始化成全 0；
    2. 反向传播时第 0 行的梯度恒为 0，训练全程它都是全 0，永不更新。

好处是什么？第 6 块的模型会把一句话的所有词向量**加起来**当句向量。
如果 <pad> 行是全 0，那么补多少个 <pad> 都不影响这个和 —— 填充对结果零污染。
如果不设 padding_idx，<pad> 会学出一个非零向量，
"补了 5 个 pad 的短句"和"补了 0 个 pad 的长句"就会被平白加进不同的偏移量。

--------------------------------------------------------------------
六、四个必踩的坑
--------------------------------------------------------------------
1. 输入必须是**整数张量**（torch.long）。传 float 直接报错 —— 它是下标，不是数值。
2. 索引必须在 [0, V-1] 内。越界在 CPU 上是 IndexError，在 GPU 上是一句
   看不懂的 "device-side assert triggered"，是新手最常见的崩溃来源。
   所以词表一定要含 <unk>，把没见过的词兜到 unk 的索引上（第 6 块会做）。
3. embedding.weight 是 nn.Parameter，requires_grad=True，会被 optimizer 更新。
   想用别人训好的词向量并冻住，就 embedding.weight.requires_grad_(False)。
4. 一次 backward 后，**只有本 batch 用到的那几行有非零梯度**，其余行梯度是 0。
   这很好理解：没参与前向计算的行，对 loss 没有任何影响。

--------------------------------------------------------------------
七、课件勘误 / 补充（对照 `3.词向量入门到文本分类实战.md`）
--------------------------------------------------------------------
· 课件 5.1 说"训练词向量就是让这个矩阵的每个元素跟着反向传播一起更新"——
  不够准确。每次 backward 只有出现过的行拿到非零梯度（见坑 4）。
  另外用 Adam 这类带动量/二阶矩状态的优化器时，梯度为 0 的行仍可能因残留动量被微调，
  这也是超大词表下有人改用 SGD 或 sparse=True 的原因之一。
· 课件 5.2 的参数表漏了 PyTorch 实际签名里的 device / dtype 两个参数（不影响使用）。
· 课件第二块（余弦相似度）那张公式图是作者本机的绝对路径
  `C:\\Users\\HUAWEI\\Desktop\\课件\\assets\\...`，你这边打不开。公式补在这里：
      cos(A, B) = (A·B) / (|A| * |B|)
      分子 A·B 是点积 = Σ A_i * B_i；分母是两个向量的模长（长度）相乘。
  除以模长就是"把两个向量都拉伸成单位长度再比"，所以它只看方向、不看长短。

运行方式：
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python text_cls/01_embedding.py
"""

import torch
import torch.nn as nn


def demo_1_lookup():
    """验证第三节的手算：Embedding 就是按行号取行。"""
    print("=" * 60)
    print("demo 1：查表 = 按行号取行")
    print("=" * 60)

    emb = nn.Embedding(num_embeddings=4, embedding_dim=3)

    # 平时权重是随机初始化的，这里手动写死成算例里的矩阵，方便和手算对照。
    # no_grad() 表示"这行赋值不要记进计算图" —— 我们在改参数本身，不是在做前向计算。
    with torch.no_grad():
        emb.weight.copy_(torch.tensor([
            [0.0, 0.1, 0.2],
            [1.0, 1.1, 1.2],
            [2.0, 2.1, 2.2],
            [3.0, 3.1, 3.2],
        ]))

    print("权重矩阵 W (4x3)：")
    print(emb.weight.data)

    idx = torch.tensor([2, 0, 3])          # 必须是整数张量
    out = emb(idx)

    print("\n输入索引:", idx.tolist())
    print("输出：")
    print(out)
    print("形状: 输入", tuple(idx.shape), "-> 输出", tuple(out.shape))


def demo_2_shape():
    """形状规则：输入形状后面追加一个 embedding_dim。"""
    print("\n" + "=" * 60)
    print("demo 2：形状规则")
    print("=" * 60)

    emb = nn.Embedding(num_embeddings=10, embedding_dim=3)

    # batch_size=2，每条序列 4 个 token —— 这就是真实训练时喂进来的形状
    x = torch.tensor([[1, 2, 4, 5],
                      [4, 3, 2, 9]])
    out = emb(x)

    print("输入 (batch=2, seq_len=4):", tuple(x.shape))
    print("输出 (batch, seq_len, embed_dim):", tuple(out.shape))
    print("注意 Embedding 没动前两个维度，只在最后加了一维 D=3")


def demo_3_onehot_equivalence():
    """验证第四节：one-hot @ W 和查表结果完全相同。"""
    print("\n" + "=" * 60)
    print("demo 3：one-hot 矩阵乘法 == 查表")
    print("=" * 60)

    V, D = 4, 3
    emb = nn.Embedding(V, D)
    with torch.no_grad():
        emb.weight.copy_(torch.tensor([
            [0.0, 0.1, 0.2],
            [1.0, 1.1, 1.2],
            [2.0, 2.1, 2.2],
            [3.0, 3.1, 3.2],
        ]))

    idx = torch.tensor([2])

    # 路线 A：查表
    by_lookup = emb(idx)

    # 路线 B：先转 one-hot，再做矩阵乘法
    # one_hot 产生的是 int64，矩阵乘法要求两边同为浮点，所以 .float()
    one_hot = torch.nn.functional.one_hot(idx, num_classes=V).float()
    by_matmul = one_hot @ emb.weight          # (1,4) @ (4,3) -> (1,3)

    print("one-hot 向量:", one_hot.tolist())
    print("查表结果    :", by_lookup.tolist())
    print("矩阵乘结果  :", by_matmul.tolist())
    print("两者相等吗  :", torch.allclose(by_lookup, by_matmul))
    print("→ 数学上等价；工程上查表省掉了那 3 次乘 0 的无用乘法（V=5万时省 49999 次）")


def demo_4_padding_and_grad():
    """padding_idx 行为，以及"只有用到的行才有梯度"。"""
    print("\n" + "=" * 60)
    print("demo 4：padding_idx 与梯度分布")
    print("=" * 60)

    emb = nn.Embedding(num_embeddings=5, embedding_dim=3, padding_idx=0)
    print("构造后第 0 行（padding 行）自动是全 0：", emb.weight.data[0].tolist())

    # 模拟一个 batch：两句话，短的那句用 0(<pad>) 补齐
    x = torch.tensor([[1, 2, 3],
                      [4, 0, 0]])          # 第二句只有 1 个真词，补了 2 个 <pad>

    out = emb(x)                            # (2, 3, 3)
    loss = out.sum()                        # 随便造一个标量 loss，只为触发 backward
    loss.backward()

    print("\n本 batch 用到的索引:", sorted(set(x.flatten().tolist())))
    print("各行梯度：")
    for i in range(5):
        g = emb.weight.grad[i]
        print(f"  行 {i}: {g.tolist()}")

    print("\n读法：")
    print("  行 1/2/3/4 被用到了 -> 梯度非 0")
    print("  行 0 是 padding_idx -> 虽然被用到 2 次，梯度仍被强制为 0，永不更新")
    print("  （若把 padding_idx 去掉，行 0 的梯度会是 2.0，pad 就会开始'学习'了）")


if __name__ == "__main__":
    torch.manual_seed(0)
    demo_1_lookup()
    demo_2_shape()
    demo_3_onehot_equivalence()
    demo_4_padding_and_grad()
