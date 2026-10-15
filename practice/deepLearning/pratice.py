import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from torchvision import datasets,transforms
from FullyConnectedNet  import FullyConnectedNet
import torch.nn.functional as F
import tqdm


def main():
    writer = SummaryWriter(log_dir='./mlp/logs')

    # 1. 判断是否使用cuda
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'using device:{device}')

    # 2. 准备数据，dataset读数据
    train_set = datasets.MNIST(root='./mlp/data',train=True,download=True,transform=transforms.ToTensor())
    test_set = datasets.MNIST(root='./mlp/data',train=False,download=True,transform=transforms.ToTensor())

    # DataLoader 负责打包，分批，迭代。打乱数据
    train_loader = DataLoader(dataset=train_set,batch_size=100,shuffle=True)
    test_loader = DataLoader(dataset=test_set,batch_size=100,shuffle=False)

    # 3. 创建模型
    model = FullyConnectedNet()
    model = model.to(device)

    # 4. 确认损失函数
    # todo 损失函数一定是这个嘛？
    loss_fn = nn.MSELoss()
    # 5. 创建优化器，使用梯度下降算法。参数的更新
    opt = torch.optim.Adam(model.parameters())

    # 早停法参数：当测试集成损失连续patience轮不再变好时，提前终止训练
    patience = 5
    best_test_loss = float('inf')
    no_improve_count =0

    max_epochs = 1000

    for epoch in range(max_epochs):
        # 6. 训练模型
        model.train()
        train_total_loss = 0
        # 
        for images,lables in tqdm.tqdm(train_loader,desc="train",total=len(train_loader)):
            images,lables = images.to(device),lables.to(device)
            lables=F.one_hot(lables,num_classes=10).float()
            outputs = model(images)
            loss = loss_fn(outputs,lables)

            opt.zero_grad()
            loss.backward()
            opt.step()
            train_total_loss += loss.item()

        train_avg_loss = train_total_loss / len(train_loader)
        print(F'Epoch{epoch+1}/{max_epochs},loss:{train_avg_loss:.4f}')

        # 7. 测试模型
        model.eval()
        test_total_loss =0
        test_total_acc=0
        # 禁用梯度计算？为什么？训练的时候不是需要反向传播去修改w和b的参数嘛
        with torch.inference_mode():
            for images,lables in tqdm.tqdm(test_loader,desc="test",total=len(test_loader)):
                images,lables = images.to(device),lables.to(device)
                lables = F.one_hot(lables,num_classes=10).float()
                outputs = model(images)
                # 计算损失
                loss = loss_fn(outputs,lables)
                test_total_loss += loss.item()

                pred = torch.argmax(outputs,dim=1)
                target = torch.argmax(lables,dim=1)
                acc = torch.eq(pred,target).float().mean()
                test_total_acc+=acc.item()

        test_avg_acc = test_total_acc / len(test_loader)
        print(f'epoch:{epoch+1},test accuracy:{test_avg_acc:.4f}')

        test_avg_loss = test_total_loss / len(test_loader)
        print(f'epoch:{epoch+1},test loss:{test_avg_loss:.4f}')

        # 记录数据
        writer.add_scalars('loss/train',{'train_avg_loss':train_avg_loss,
        'test_avg_loss':test_avg_loss},epoch)
        writer.add_scalar('Accuracy/test',test_avg_acc,epoch)

        # 8. 早停判断与模型保存
        if test_avg_loss < best_test_loss:
            best_test_loss = test_avg_loss
            no_improve_count = 0
            torch.save(model.state_dict(),'./mlp/model/mnist_net_best.pth')
            print(f'测试损失改善，保存最优模型（best loss：{best_test_loss:.4f}')
        else:
            # 测试损失没有变好：计数器+1
            no_improve_count +=1
            print(f'测试损失未改善({no_improve_count}/{patience})')
            if no_improve_count >= patience:
                print(f'早停：测试损失连续{patience}轮未改善，在第{epoch+1}轮终止训练')
                break;

if __name__ == '__main__':
    main()            
        