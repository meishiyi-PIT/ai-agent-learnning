"""
模块五 · 第 6 节 · 6.2 第 4 段：训练 + 测试 + 早停
=====================================================
课件"重要步骤 3：文本分类模型的训练和测试"。八步旅程的第 7、8 步。

【和 CNN 那节的训练脚本比，哪些是一样的】（🟢 扫过即可）
    DEVICE 选择 / model.train() + 前向 + loss + zero_grad + backward + step /
    model.eval() + inference_mode() + argmax 算准确率 / SummaryWriter 记曲线 / torch.save 存权重
    —— 逐行同款，不重复讲。

【这节新的三件事】（🔴）
  1. 运行顺序 = 先数据后模型：
         NewsDataset → build_vocab → 词表长度 & <pad> 号码 → 才能 new TextClassifier
     因为 vocab_size（W 的行数）和 padding_idx 都得等词表建完才知道。课件写代码顺序是
     "先 net.py 再 data.py"，运行顺序正相反。
  2. collate_fn：DataLoader 抓出来的一批 (tokens, label) 长短不一，必须经 collate_batch 查 ID + 补 pad。
         collate = lambda batch: collate_batch(batch, text_vocab)
     这个 lambda 是为了把 text_vocab 也带进去——DataLoader 调 collate_fn 时只传 batch 一个参数，
     用 lambda 包一层把第二个参数"预先绑定"上（Java 里类似闭包捕获局部变量）。
  3. 早停（early stopping）：
         每个 epoch 结束看测试 loss；比历史最好还低 → 记下、存模型、计数清零；
         没变好 → 计数 +1；连续 patience=6 轮没变好 → break。
     它解决的是 CNN 那节讲的过拟合"剪刀口"：训练 loss 还在降、测试 loss 开始回升时，
     再训下去只是在背答案，不如停在测试 loss 最低点。for range(2000) 只是上限，实际靠早停结束。

【课件参数有两处要改，理由写在这】
  · batch_size=22000（一批 2.2 万句）：句长最长 203，每批几乎必撞长句 → L≈200，
    Embedding 输出 [22000, 200, 256] 个 float32 = 4.5 GB，CPU 笔记本直接爆内存。
    这里改成 512（[512, 200, 256] ≈ 100 MB）。老师的机器有大显存才敢这么写。
  · 测试集 batch_size=7600 是把整个测试集当一批，同理改小；不影响准确率，只影响内存。

【方法论上的一个问题（课件没说）】
    早停用的是**测试集** loss，最后报告的也是**测试集**准确率——测试集参与了"什么时候停"这个决策，
    报出来的分数会略偏乐观。规范做法是从训练集再切一块验证集（validation）做早停，测试集只在最后看一次。
    教学演示可以接受，做实验/写论文不行。

【一个小瑕疵】
    准确率是"每批 acc 求平均"，最后一批比其他批小，权重却一样 → 有极小偏差。
    精确做法是累计 correct 数 / 总样本数。这里按精确做法写。

运行：
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python text_cls/train.py
    看曲线：uv run tensorboard --logdir text_cls/logs
    快速冒烟（只跑 1 轮）：MAX_EPOCHS=1 PYTHONUTF8=1 uv run python text_cls/train.py
"""

import os
import time
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter

from data import NewsDataset
from net import TextClassifier
from utils import build_vocab, collate_batch

HERE = Path(__file__).resolve().parent
LOG_DIR = HERE / "logs"
MODEL_PATH = HERE / "model" / "net_best.pth"
MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MAX_EPOCHS = int(os.environ.get("MAX_EPOCHS", 2000))   # 上限，实际靠早停结束
BATCH_SIZE = 512

# ---------- 1. 数据（必须在模型之前） ----------
t0 = time.time()
train_dataset = NewsDataset(is_train=True)
test_dataset = NewsDataset(is_train=False)
text_vocab = build_vocab(train_dataset)        # 词表只用训练集建：测试集的词模型本来就不该见过
print(f"text vocab: {len(text_vocab)}   (数据+词表耗时 {time.time() - t0:.1f}s)")

collate = lambda batch: collate_batch(batch, text_vocab)
train_dataloader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, collate_fn=collate)
test_dataloader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False, collate_fn=collate)

# ---------- 2. 模型（两个参数来自词表） ----------
vocab_size = len(text_vocab)                   # W 的行数
embed_dim = 256                                # W 的列数
num_classes = 4
padding_idx = text_vocab["<pad>"]              # 和 collate_batch 里补的是同一个号码（=1）

model = TextClassifier(vocab_size, embed_dim, num_classes, padding_idx).to(DEVICE)
opt = torch.optim.Adam(model.parameters())
loss_fn = nn.CrossEntropyLoss()
writer = SummaryWriter(str(LOG_DIR))

# ---------- 3. 训练 + 测试 + 早停 ----------
print("begin train:")
patience = 6
best_test_loss = float("inf")
no_improve_count = 0

for epoch in range(MAX_EPOCHS):
    t_epoch = time.time()

    # --- 训练：和 CNN 那节逐行相同 ---
    model.train()
    train_sum_loss = 0
    for text, label in train_dataloader:       # text: [B, L] 整数，label: [B]
        text, label = text.to(DEVICE), label.to(DEVICE)
        out = model(text)                      # [B, 4] logits
        loss = loss_fn(out, label)
        opt.zero_grad()
        loss.backward()
        opt.step()
        train_sum_loss += loss.item()
    train_avg_loss = train_sum_loss / len(train_dataloader)

    # --- 测试：不更新参数 ---
    model.eval()
    test_total_loss = 0
    correct = 0
    with torch.inference_mode():
        for text, label in test_dataloader:
            text, label = text.to(DEVICE), label.to(DEVICE)
            out = model(text)
            test_total_loss += loss_fn(out, label).item()
            preds = torch.argmax(out, dim=1)   # 每行分最高的格子 = 预测类别
            correct += (preds == label).sum().item()
    test_avg_loss = test_total_loss / len(test_dataloader)
    test_acc = correct / len(test_dataset)

    print(f"epoch:{epoch + 1} train_loss:{train_avg_loss:.4f} test_loss:{test_avg_loss:.4f} "
          f"test_acc:{test_acc:.4f} ({time.time() - t_epoch:.0f}s)")
    writer.add_scalars("loss", {"train": train_avg_loss, "test": test_avg_loss}, epoch)
    writer.add_scalar("test_acc", test_acc, epoch)

    # --- 早停判断 + 只保存最优 ---
    if test_avg_loss < best_test_loss:
        best_test_loss = test_avg_loss
        no_improve_count = 0
        torch.save(model.state_dict(), MODEL_PATH)
        print(f"  测试损失改善，保存最优模型 (best loss: {best_test_loss:.4f})")
    else:
        no_improve_count += 1
        print(f"  测试损失未改善 ({no_improve_count}/{patience})")
        if no_improve_count >= patience:
            print(f"早停：测试损失连续 {patience} 轮未改善，在第 {epoch + 1} 轮终止训练")
            break

writer.close()
