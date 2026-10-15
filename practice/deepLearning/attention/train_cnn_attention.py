"""
模块五 · 《注意力机制》第六节 动手实战（挖空版）：CNN + 多头自注意力 做 CIFAR-10 分类
=====================================================================================
课件只给了 CNNWithAttention 的模型定义（见 cnn_attention.py），没给数据和训练循环。
这里用 CNN 那节用过的 CIFAR-10（32×32，10 类）把它真正跑起来，并和"同一个网络去掉注意力"做对照。

【和课件模型的差别（为了适配 32×32 和 CPU）】
  · 课件输入 112×112、5 层不带 padding 的卷积，末端特征图 20×20；CIFAR 是 32×32，
    照抄会在第 5 层被"减"成负数。这里用 3 层 padding=1 的卷积 + 2 次池化：32 → 16 → 8，特征图 [N, 128, 8, 8]。
  · 课件把 400×256 拍平接 fc（61 万参数）；这里注意力之后对 64 个位置取平均（全局平均池化）再接 fc(128, 10)。
  · use_attention=False 时跳过注意力，直接对特征图取平均 —— 这是对照组，其余完全一样。

【你要填的 TODO（共 7 处，全部是学过的）】
  TODO 1-2  forward 里"特征图 → 句子"的两行（cnn_attention.py 里刚讲过：permute + reshape）
  TODO 3-5  训练循环三件套（LeNet5 / text_cls/train.py 里写过：前向+loss、清梯度+反传+更新）
  TODO 6-7  测试里的 argmax 和计数（text_cls/train.py 同款）
  卡住 20 分钟再看提示；提示在每个 TODO 旁边的注释里。

【怎么跑】
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python attention/train_cnn_attention.py                  # 带注意力，5 轮
    USE_ATT=0 PYTHONUTF8=1 uv run python attention/train_cnn_attention.py        # 对照组：不带注意力
    SUBSET=5000 EPOCHS=1 ... 先用 5000 张图跑 1 轮确认能通，再跑全量
  CPU 上全量一轮约 2-4 分钟。两组各跑 5 轮，比较 test_acc —— 这就是这节的产出物。

【预期看到什么】
  两组差距不会很大（CIFAR 32×32 太小，卷积感受野已经够覆盖全图，注意力的"远距离"优势发挥不出来）。
  这本身就是结论：注意力不是万能加分项，它补的是"远距离交互"，图小的时候没有远距离可补。
  想看到差距：把输入放大（transforms.Resize(64)）或减少卷积层数让感受野变小。
"""

import os
import time

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms

from multi_head import MultHeadedAttention

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
EPOCHS = int(os.environ.get("EPOCHS", 5))
SUBSET = int(os.environ.get("SUBSET", 0))          # >0 时只用前 SUBSET 张训练图（冒烟用）
USE_ATT = os.environ.get("USE_ATT", "1") == "1"
DATA_ROOT = "c:/workspace/gitcode/cnn/data"        # CNN 那节下载 CIFAR-10 的位置


class CNNWithAttentionCIFAR(nn.Module):
    def __init__(self, num_classes=10, use_attention=True):
        super().__init__()
        self.use_attention = use_attention
        self.conv_layers = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1, bias=False), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),   # 32 → 16
            nn.Conv2d(32, 64, 3, padding=1, bias=False), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),  # 16 → 8
            nn.Conv2d(64, 128, 3, padding=1, bias=False), nn.BatchNorm2d(128), nn.ReLU(),                 # 8 → 8
        )
        # 每个空间位置当一个 token，128 个通道值就是它的向量；8×8 = 64 个 token
        # 对照组不建这层，这样两组打印出来的 params 差值 = 注意力层的参数量（4 张 128×128 的表 = 65536）
        self.attention = MultHeadedAttention(d_model=128, n_head=4) if use_attention else None
        self.fc = nn.Linear(128, num_classes)

    def forward(self, x):
        x = self.conv_layers(x)                          # [N, 128, 8, 8]   N C H W
        if self.use_attention:
            # TODO 1：把通道挪到最后 → [N, 8, 8, 128]      提示：permute，四个维度按 N H W C 的顺序写下标
            x = ...
            # TODO 2：64 个位置拍成一串 → [N, 64, 128]     提示：reshape(N, -1, C)，N 用 x.size(0)，C 用 x.size(-1)
            x = ...
            x = self.attention(x, x, x)                  # [N, 64, 128]  自注意力：每个位置看全图
            x = x.mean(dim=1)                            # [N, 128]      64 个位置取平均
        else:
            x = x.mean(dim=(2, 3))                       # [N, 128]      对照组：直接对 H、W 取平均
        return self.fc(x)                                # [N, 10]


# ---------- 数据 ----------
train_set = datasets.CIFAR10(root=DATA_ROOT, train=True, download=True, transform=transforms.ToTensor())
test_set = datasets.CIFAR10(root=DATA_ROOT, train=False, download=True, transform=transforms.ToTensor())
if SUBSET:
    train_set = Subset(train_set, range(SUBSET))
    test_set = Subset(test_set, range(SUBSET // 5))
train_loader = DataLoader(train_set, batch_size=128, shuffle=True)
test_loader = DataLoader(test_set, batch_size=256, shuffle=False)

# ---------- 模型 ----------
model = CNNWithAttentionCIFAR(use_attention=USE_ATT).to(DEVICE)
loss_fn = nn.CrossEntropyLoss()
opt = torch.optim.Adam(model.parameters())
print(f"use_attention={USE_ATT}  params={sum(p.numel() for p in model.parameters())}  device={DEVICE}")

# ---------- 训练 + 测试 ----------
for epoch in range(EPOCHS):
    t0 = time.time()

    model.train()
    total_loss = 0
    for images, labels in train_loader:
        images, labels = images.to(DEVICE), labels.to(DEVICE)
        # TODO 3：前向 + 算 loss                          提示：out = model(...)；loss = loss_fn(out, ...)
        ...
        # TODO 4：清梯度 → 反向传播 → 更新参数（三行）     提示：opt / loss / opt 各一行
        ...
        # TODO 5：累加 loss 的数值                         提示：.item()
        ...
    train_loss = total_loss / len(train_loader)

    model.eval()
    correct = 0
    with torch.inference_mode():
        for images, labels in test_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            out = model(images)
            # TODO 6：每行取分最高的类别                    提示：torch.argmax(..., dim=1)
            preds = ...
            # TODO 7：累加预测对的个数                      提示：(preds == labels).sum().item()
            ...
    test_acc = correct / len(test_set)

    print(f"epoch {epoch + 1}  train_loss {train_loss:.4f}  test_acc {test_acc:.4f}  ({time.time() - t0:.0f}s)")
