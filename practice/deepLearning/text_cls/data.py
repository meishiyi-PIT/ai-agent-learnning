"""
模块五 · 第 6 节 · 6.2 数据准备：NewsDataset
=================================================
课件"重要步骤 2"的第 1 段代码。八步旅程的第 1 步：读 csv → 切词。

【在流水线里的位置】
    csv 文件  →  ★本文件：读出来、切成词、存成 (tokens, label) 列表★  →  utils.py 建词表 / 补 pad  →  net.py

【Dataset 是什么】
    PyTorch 约定的"数据仓库"接口，和 CNN 那节的 CIFAR10 同款：只要实现
        __len__      一共多少条
        __getitem__  第 i 条是什么
    DataLoader 就能按 batch_size 从里面抓数据、洗牌、交给 collate_fn。
    这里 __init__ 一次性把全部 12 万条切好词放进 self.examples（list），__getitem__ 直接取下标。

【AG News 的 csv 长什么样】（readme.txt）
    每行 3 列：类别(1~4)，标题，正文描述；**没有表头行**。
    1=World 2=Sports 3=Business 4=Tech（classes.txt），训练集每类 3 万条共 12 万，测试集 7600。

【切词 basic_english 做了什么】
    小写 → 标点前后加空格 → 按空格切。"Wall St. Bears" → ['wall', 'st', '.', 'bears']。
    标点也算一个 token，会进词表，无伤大雅。
    课件在外面又套了一层 token.lower()，其实 basic_english 内部已经小写过了，多此一举但无害。

【课件勘误——已在本文件修正】
  1. `pd.read_csv(path)` 没写 header=None。csv 没有表头，pandas 默认把**第一行当列名吃掉**，
     训练集变成 119999 条，第一条新闻（"Wall St. Bears Claw Back..."）永久丢失。
     实测：默认 → 119999 行，列名变成 ['3', 'Wall St. Bears ...', ...]；header=None → 120000 行。
     测试集同理少 1 条。分类效果几乎不受影响，但这是个真 bug，而且 `data[0]` 的注释
     "Wall St. Bears..." 在原代码下根本取不到。
  2. 路径 "./text_cls/ag_news_csv/train.csv" 依赖运行时 cwd；这里改成相对本文件解析，
     在哪个目录运行都能找到（和 Agentic_Rag 的 config.py 同一约定）。

【一个设计选择，不是 bug】
    课件只用第 2 列（正文描述），第 1 列标题没用。标题信息密度其实更高，
    把 title + " " + description 拼起来一般能再涨一点准确率；这里保持课件行为，
    想试的话改 TEXT_COLUMNS 即可。

【Python 语法点】
    pd.read_csv(..., header=None)  返回 DataFrame（表格），列名是 0/1/2
    for index, row in data.iterrows()  逐行遍历，row 是一行（Series），row.iloc[k] 取第 k 列
    self.examples.append((tokenized_text, label))  往 list 里塞一个二元组，取的时候 text, label = ex

运行：
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python text_cls/data.py
"""

from pathlib import Path

import pandas as pd
import torchtext
from torch.utils.data import Dataset
from torchtext.data.utils import get_tokenizer

torchtext.disable_torchtext_deprecation_warning()   # torchtext 0.18 是绝版，每次 import 都会刷一段警告，关掉

DATA_DIR = Path(__file__).resolve().parent / "data" / "ag_news_csv"
TEXT_COLUMNS = [2]          # 课件只用正文；改成 [1, 2] 则标题+正文拼接


class NewsDataset(Dataset):
    """把 AG News 的 csv 读成 [(tokens, label), ...]。label 保持原始 1~4，减 1 的事交给 collate_batch。"""

    def __init__(self, is_train=True) -> None:
        super().__init__()
        csv_path = DATA_DIR / ("train.csv" if is_train else "test.csv")
        data = pd.read_csv(csv_path, header=None)          # header=None：csv 没有表头行

        tokenizer = get_tokenizer("basic_english")         # 内置英文切词器（已含小写）
        self.examples = list()
        for index, row in data.iterrows():
            label = int(row.iloc[0])                       # 1~4
            text = " ".join(str(row.iloc[c]) for c in TEXT_COLUMNS)
            # 原始 csv 把换行写成了一个反斜杠（"dwindling\band"），不处理会切出 'dwindling\band' 这种脏 token
            text = text.replace("\\", " ")
            tokenized_text = tokenizer(text)               # str -> list[str]
            self.examples.append((tokenized_text, label))

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, index):
        return self.examples[index]


if __name__ == "__main__":
    import time

    t0 = time.time()
    dataset = NewsDataset(is_train=True)
    print(f"训练集条数: {len(dataset)}   (课件原代码会得到 119999，见 docstring 勘误 1)")
    print(f"切词耗时: {time.time() - t0:.1f}s")

    tokens, label = dataset[0]
    print("\ndataset[0]:")
    print("  label  =", label, "(3 = Business)")
    print("  tokens =", tokens)
    print("  词数   =", len(tokens))

    # 看看句子长度分布：决定了 collate 时 L 会有多大
    lengths = [len(t) for t, _ in dataset.examples]
    print(f"\n句长统计: 最短 {min(lengths)}，最长 {max(lengths)}，平均 {sum(lengths) / len(lengths):.1f}")
