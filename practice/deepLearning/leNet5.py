import torch
from torch import nn

class LeNet5(nn.Module):
    def __init__(self):
        super().__init__()
        #特征提取器 Conv → ReLU → Pool 反复出现
        #卷积提取局部模式，ReLU 引入非线性，池化降低空间分辨率并扩大有效视野。
        self.conv1 = nn.Sequential(
            nn.Conv2d(in_channels=3, 
                      out_channels=6, 
                      kernel_size=5, 
                      stride=1, 
                      padding=0),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2, padding=0)
        )
        
        self.conv2 = nn.Sequential(
            nn.Conv2d(in_channels=6, 
                      out_channels=16, 
                      kernel_size=5,
                      stride=1, 
                      padding=0),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2, padding=0)
            # nn.MaxPool2d(kernel_size=2, stride=2, padding=0)  == nn.MaxPool2d(kernel_size=2)   
        )
        
        self.flatten = nn.Flatten()
        
        self.fc1 = nn.Sequential(
            nn.Linear(400, 120),
            nn.ReLU()
        )
        
        self.fc2 = nn.Sequential(
            nn.Linear(120, 84),
            nn.ReLU()
        )
        
        self.fc3 = nn.Linear(84, 10)
        
    def forward(self, x):   
        out = self.conv1(x)
        out = self.conv2(out)
        out = self.flatten(out)
        out = self.fc1(out)
        out = self.fc2(out)
        
        logits = self.fc3(out)
  
        return logits

if __name__ == '__main__':
    net = LeNet5()
    data = torch.randn(1, 3, 32, 32)
    output = net(data)
    print(output)