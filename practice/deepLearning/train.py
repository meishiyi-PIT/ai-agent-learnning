from torch.utils.data import DataLoader
import torch
from torch import nn
from torch.utils.tensorboard import SummaryWriter
from NewDataSet import NewsDataset,build_vocab,collate_batch
from TextClassifier import TextClassifier

writer = SummaryWriter("./text_cls/logs")
DEVICE=torch.device("cuda" if torch.cuda.is_available() else "cpu")

train_dataset = NewsDataset(True)
test_dataset = NewsDataset(False)

text_vocab=build_vocab(train_dataset)
print("text vocab:",len(text_vocab))

collate=lambda batch: collate_batch(batch,text_vocab)
train_dataloader=DataLoader(train_dataset,batch_size=22000,shuffle=True, collate_fn=collate)
test_dataloader = DataLoader(test_dataset,batch_size=7600,shuffle=False, collate_fn=collate)

vocab_size=len(text_vocab)
embed_dim=256
num_classes=4
padding_idx=text_vocab['<pad>']

model=TextClassifier(vocab_size,
                     embed_dim,
                     num_classes,
                     padding_idx)
model=model.to(DEVICE)
opt = torch.optim.Adam(model.parameters())
loss_fn = nn.CrossEntropyLoss()

print("begin train：")

patience = 6
best_test_loss = float('inf')
no_improve_count = 0
for epoch in range(2000):
    train_sum_loss = 0
    model.train()

    for i,(text,label) in enumerate(train_dataloader):
        text = text.to(DEVICE)
        label = label.to(DEVICE)

        out = model(text)
        loss = loss_fn(out,label)

        opt.zero_grad()
        loss.backward()
        opt.step()

        train_sum_loss+=loss.item()
    train_avg_loss = train_sum_loss/len(train_dataloader)

    test_sum_acc = 0
    test_total_loss = 0
    model.eval()    
    with torch.inference_mode():
        for i,(text,label) in enumerate(test_dataloader):
            text = text.to(DEVICE)
            label = label.to(DEVICE)
            out = model(text)

            loss = loss_fn(out,label)
            test_total_loss+=loss.item()

            preds = torch.argmax(out,dim=1)
            acc = torch.mean(torch.eq(preds,label).to(torch.float32))
            test_sum_acc+=acc.item()

        test_avg_acc = test_sum_acc /len(test_dataloader)
        test_avg_loss = test_total_loss /len(test_dataloader)
        print(f"epoch:{epoch+1} train_avg_loss:{train_avg_loss} test_avg_loss:{test_avg_loss} test_avg_acc:{test_avg_acc}")

    writer.add_scalars("loss", {"train": train_avg_loss, "test": test_avg_loss}, epoch)
    writer.add_scalar("test_avg_acc", test_avg_acc, epoch)

    #早停判断与模型保存
    if test_avg_loss < best_test_loss:
        # 测试损失变好了：更新最好成绩，重置计数器，保存当前最优模型
        best_test_loss = test_avg_loss
        no_improve_count = 0
        torch.save(model.state_dict(), './text_cls/model/net_best.pth')
        print(f'测试损失改善，保存最优模型 (best loss: {best_test_loss:.4f})')
    else:
        # 测试损失没有变好：计数器加一
        no_improve_count += 1
        print(f'测试损失未改善 ({no_improve_count}/{patience})')
        if no_improve_count >= patience:
            # 连续 patience 轮没有变好，提前终止训练
            print(f'早停：测试损失连续 {patience} 轮未改善，在第 {epoch+1} 轮终止训练')
            break   

