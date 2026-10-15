import torch
import torch.nn.functional as F
from torch import nn

class ResBlock(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.conv1 = torch.nn.Conv2d(c,c,3,padding=1)
        self.conv2 = torch.nn.Conv2d(c,c,3,padding=1)

    def forward(self,
                x):
        y = F.relu(self.conv1(x))
        y = self.conv2(y)
        return F.relu(y+x)

class Net(torch.nn.Module):
    def __init__(self, *args, **kwargs):
        super(Net,self).__init__(*args, **kwargs)
        self.conv1 = torch.nn.Conv2d(3,64,3,1)
        self.resblock = ResBlock(64)
        self.conv2 = torch.nn.Conv2d(64,128,1,1)

    def forward(self,x):
        out = self.conv1(x)
        x = self.resblock(out)
        y = self.conv2(x)
        return y    

if __name__ =='__main__':
    x = torch.randn(1,3,32,32)
    net = ResBlock(3)
    out = net(x)    
    print(out)
    print(out.shape)
