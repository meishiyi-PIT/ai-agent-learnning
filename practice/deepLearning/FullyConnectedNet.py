from torch import nn
import torch

class FullyConnectedNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.layer = nn.Sequential(
            nn.Flatten(),
            nn.Linear(28*28,512),
            nn.ReLU(),
            nn.Linear(512,256),
            nn.ReLU(),
            nn.Linear(256,128),
            nn.ReLU(),
            nn.Linear(128,10),
            nn.Softmax(dim=1)
        )

    def forward(self,x):
        return self.layer(x)


if __name__ == '__main__':
        data = torch.randn(1,1,28,28)
        net = FullyConnectedNet()
        output = net(data)
        print(output)