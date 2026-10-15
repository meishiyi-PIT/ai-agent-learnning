import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from torchvision import datasets,transforms
from leNet5 import LeNet5
import tqdm

# 指定日志目录
writer = SummaryWriter(log_dir="c:/workspace/gitcode/cnn/logs")

# 1. 判断是否使用CUDA
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'Using device:{device}')

# 2. 准备数据
train_set = datasets.CIFAR10(root='c:/workspace/gitcode/cnn/data',train=True,download=True,transform=transforms.ToTensor())
test_set = datasets.CIFAR10(root='c:/workspace/gitcode/cnn/data',train=False,download=True,transform=transforms.ToTensor())
train_loader = DataLoader(dataset=train_set
                          ,batch_size=100,shuffle=True)
test_loader = DataLoader(dataset=test_set,batch_size=100,shuffle=False)

# 3. 创建模型
model = LeNet5()
model = model.to(device)

# 4. 确认损失函数
loss_fn = nn.CrossEntropyLoss()

# 5. 创建优化器，使用梯度下降算法，参数的更新
opt = torch.optim.Adam(model.parameters())

for epoch in range(100):
    # 6. 训练模型
    model.train()
    train_total_loss = 0
    for images, labels in tqdm.tqdm(train_loader,desc="train",total=len(train_loader)):
        # 将数据移动到设备
        images,labels = images.to(device),labels.to(device)
        ouputs = model(images) # 前向传播
        loss = loss_fn(ouputs,labels) # 计算损失

        opt.zero_grad() # 清空梯度
        loss.backward() # 反向传播，计算梯度
        opt.step() # 更新参数
        train_total_loss += loss.item()
    train_avg_loss = train_total_loss / len(train_loader)
    print(f'Epoch {epoch+1},loss:{train_avg_loss:.4f}')
    # 7. 测试模型    
    model.eval()
    test_total_loss = 0
    test_total_acc = 0

    with torch.inference_mode():
        for images,labels in tqdm.tqdm(test_loader,desc="test",total=len(test_loader)):
            images ,labels =images.to(device),labels.to(device)
            outputs=model(images)
            # 计算损失
            loss = loss_fn(ouputs,labels)
            test_total_loss += loss.item()

            pred = torch.argmax(outputs,labels)
            acc = torch.eq(pred,labels).float().mean()
            test_total_acc += acc.item()

    test_avg_acc = test_total_acc / len(test_loader)
    print(f'Epoch {epoch+1},test accuracy:{test_avg_acc:.4f}')        

    test_avg_loss = test_total_loss / len(test_loader)
    print(f'Epoch {epoch+1} test loss:{test_avg_loss:.4f}')

    # 记录数据
    writer.add_scalars('Loss/train',{'train_avg_loss':train_avg_loss
                        ,'test_avg_loss':test_avg_loss},epoch)
    writer.add_scalar('Accuracy/test',test_avg_acc,epoch)
    # 8. 保存模型
    torch.save(model.state_dict(),'c:/workspace/gitcode/cnn/model/lenet.pth')

