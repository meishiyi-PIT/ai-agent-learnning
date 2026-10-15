import torch
import torch.nn as nn
import torch.nn.functional as F

class simpleCNN(nn.Module):
    def __init__(self, num_classes=10):
        super(simpleCNN,self).__init__()

        # 特征提取器
        # conv -> relu -> pool
        # 卷积提取局部模型，relu引入非线性，池化降低空间分辨率并扩大有效视野
        self.conv1 = nn.Sequential(
            #第一个卷积块
            nn.Conv2d(3,16,kernel_size=3,padding=1),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2),
        )

        self.conv2 = nn.Sequential(
            # 第二个卷积块
            nn.Conv2d(16,32,kernel_size=3,padding=1),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2),
        )

        self.conv3 = nn.Sequential(
            # 第三个卷积块
            nn.Conv2d(32,64,kernel_size=3),
            nn.ReLU()
        )

        self.conv4 = nn.Sequential(
            # 第四个卷积块
            nn.Conv2d(64,128,kernel_size=3),
            nn.ReLU()
        )

        # 分类器 处理卷积层提炼后的高层特征，最终输出类别得分
        # Flatten 特征图拉出一维向量
        # Linear 映射到类别数维度
        # softmax 推理时 转成概率分布
        self.fc = nn.Sequential(
            # 展平层
            nn.Flatten(),
            # 全连接层
            nn.Linear(128*4*4,num_classes),
            nn.Softmax(dim=1)
        )

    def forward(self,x):
        conv_out = self.conv1(x)
        conv_out = self.conv2(conv_out)    
        conv_out = self.conv3(conv_out)   
        conv_out = self.conv4(conv_out)
        out = self.fc(conv_out)
        return out

if __name__ == '__main__':
    data = torch.randn(1,3,32,32)
    model = simpleCNN()
    output = model(data)
    print(output)
    print(f"输出形状：{output.shape}")       