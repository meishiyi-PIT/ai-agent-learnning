"""
模块五 · 第 6 节 · 6.2 数据准备：词表 + 填充
=================================================
课件"重要步骤 2"的第 2、3 段代码（build_vocab / collate_batch）。
课件依赖 torchtext（本机 torch 2.13 下无法加载），这里用纯 Python 等价实现，
逻辑与 torchtext 逐行对应，但你能看见词表内部到底是什么。

【在流水线里的位置】
    data.py 切好词  →  ★build_vocab：词 → ID 对照表★  →  ★collate_batch：查 ID + 补 pad★  →  net.py
    八步旅程的第 2 步（查 ID）和第 3 步（补 pad）都在本文件。

【词表（Vocab）是什么】
    就是一个 dict：{词: 整数 ID}。课件那张"word -> index"图就是它。
    ID 就是第 5 节 Embedding 表 W 的行号，所以词表有多少个词，W 就要有多少行
    （train.py 里 vocab_size = len(text_vocab) 就是这么来的）。

【两个特殊词，各解决一个问题】
    <unk>  没见过 / 太生僻的词都归它。没有它，测试集出现新词就查不到 → 越界崩溃（第 5 节坑 2）。
    <pad>  补位用的假词。它的 ID 会传给 Embedding 的 padding_idx，那一行恒为 0。
    specials 排在词表最前面按顺序编号：<unk> = 0，<pad> = 1。

【min_freq=2 为什么要过滤低频词】
    出现 1 次的词，它那一行 W 只会被磨 1 次，向量基本还是初始噪声，留着没用还撑大词表；
    统统归 <unk>。AG News 12 万条不过滤约 9 万词，过滤后约 6 万。

【collate_batch 是干什么的】
    DataLoader 每次从 Dataset 取出 batch_size 条 (tokens, label)，把它们交给 collate_fn，
    要求它返回"能直接喂模型的张量"。默认的 collate 只会把等长的东西摞起来，
    句子长短不一它会报错，所以要自己写：先每句查 ID 变整数张量，再 pad_sequence 补齐摞成 [B, L]。

【pad_sequence 三个参数】
    text_list             一批长短不一的一维整数张量
    batch_first=True      返回 [B, L]；不写会返回 [L, B]（老坑，模型 forward 会错位）
    padding_value=1       用 <pad> 的 ID 补，必须和 Embedding 的 padding_idx 是同一个数

【label - 1 为什么】
    AG News 的标签是 1~4，CrossEntropyLoss 要求类别从 0 编号（同 Java 数组），所以减 1 变 0~3。

【Python 语法点】
    lambda x: x[0]        匿名函数，等价 def f(x): return x[0]；这里 x 是 (tokens, label)，取 tokens
    map(f, iterable)      对每个元素调 f，惰性求值（不真的算，迭代时才算），类似 Java Stream.map
    Counter               dict 子类，update(list) 会给列表里每个元素计数 +1
    [expr for t in xs]    列表推导式 = 一行 for 循环收集结果
    torch.stack           把 N 个同形状张量摞成 N 维；标签都是标量，摞成 [B]

运行：
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python text_cls/utils.py
"""

from collections import Counter

import torch
from torch.nn.utils.rnn import pad_sequence


class Vocab:
    """词 → ID 的对照表。等价于 torchtext.vocab.Vocab 常用的那几个方法。"""

    def __init__(self, token_iter, min_freq=1, specials=()):
        counter = Counter()
        for tokens in token_iter:          # 每个元素是一句话切好的词列表
            counter.update(tokens)

        self.itos = list(specials)         # index -> string：specials 排最前，按给定顺序编号
        for token, freq in counter.most_common():   # 按词频从高到低
            if freq < min_freq:
                break                      # most_common 已排序，后面的更低，直接停
            if token not in specials:
                self.itos.append(token)

        self.stoi = {tok: i for i, tok in enumerate(self.itos)}   # string -> index
        self.default_index = None

    def set_default_index(self, idx):
        """查不到的词返回这个 ID（一般设成 <unk> 的 ID）。"""
        self.default_index = idx

    def __getitem__(self, token):
        """让 vocab["word"] 能用。查不到且没设默认值就报错（和 torchtext 行为一致）。"""
        if token in self.stoi:
            return self.stoi[token]
        if self.default_index is None:
            raise KeyError(token)
        return self.default_index

    def __len__(self):
        return len(self.itos)


def build_vocab(dataset):
    """课件第 2 段：基于 dataset 建词表。dataset 的每个元素是 (tokens, label)。"""
    special = ['<unk>', '<pad>']                      # <unk> -> 0, <pad> -> 1
    text_iter = map(lambda x: x[0], dataset)          # 只取每条的 tokens，丢掉 label
    text_vocab = Vocab(text_iter, min_freq=2, specials=special)
    text_vocab.set_default_index(text_vocab['<unk>']) # 查不到的词 -> 0
    return text_vocab


def collate_batch(batch, text_vocab):
    """课件第 3 段：DataLoader 的回调。一批 (tokens, label) -> (text_padded [B, L], labels [B])。"""
    text_list = list()
    labels = list()
    for text, label in batch:
        text_tokens = [text_vocab[token] for token in text]          # 词 -> ID（第 2 步）
        text_tensor = torch.tensor(text_tokens, dtype=torch.long)   # Embedding 只吃整数
        text_list.append(text_tensor)
        labels.append(torch.tensor(label - 1, dtype=torch.long))    # 1~4 -> 0~3

    padding_idx = text_vocab["<pad>"]                                # 查出 pad 的号码（=1）
    text_padded = pad_sequence(text_list, batch_first=True, padding_value=padding_idx)  # 补 pad（第 3 步）
    labels_tensor = torch.stack(labels)
    return text_padded, labels_tensor


if __name__ == "__main__":
    # 一个 4 条样本的迷你"数据集"，格式和 data.py 的 NewsDataset 一样：(tokens, label)
    tiny_dataset = [
        (["allardyce", "wins", "again"], 2),
        (["stocks", "fall", "again"], 3),
        (["stocks", "rise", "on", "oil", "news"], 3),
        (["wins", "for", "oil"], 2),
    ]

    vocab = build_vocab(tiny_dataset)
    print("词表（index -> word）：")
    for i, w in enumerate(vocab.itos):
        print(f"  {i:2d} -> {w}")
    print("  （allardyce/fall/rise/on/news/for 只出现 1 次，被 min_freq=2 过滤，查它们都得到 <unk>=0）")
    print("vocab_size =", len(vocab))

    print("\n单个词查 ID：")
    for w in ["again", "stocks", "allardyce", "从没见过的词"]:
        print(f"  {w!r:16} -> {vocab[w]}")

    # 取前 3 条当一个 batch，模拟 DataLoader 调 collate_fn
    batch = tiny_dataset[:3]
    print("\ncollate_batch 之前（每句各自的 ID 列表，长度不一）：")
    for tokens, label in batch:
        print(f"  {[vocab[t] for t in tokens]}   label={label}")

    text_padded, labels = collate_batch(batch, vocab)
    print("\ncollate_batch 之后：")
    print("text_padded shape =", tuple(text_padded.shape), "  <- [B, L]，L = 最长那句的长度")
    print(text_padded)
    print("labels =", labels.tolist(), "  <- 原标签减 1")
