import torch
import torch.nn as nn

class TextClassifier(nn.Module):
    def __init__(self,  vocab_size,embed_dim,num_classes,padding_idx):
        super().__init__()
        #定义一个词嵌入层
        #embeddin
        # g层的大小是vocab_size*embed_dim,表示词表大小乘以词向量的维度
        # 5000*128
        self.embedding = nn.Embedding(vocab_size,embed_dim,padding_idx=padding_idx)    
        #定义一个线性层
        #线性层的大小是 embed_dim*num_classes,表示词向量维度乘以类别数量
        #例如 128*4       
        self.fc = nn.Sequential(
            nn.Linear(embed_dim,128),
            nn.BatchNorm1d(128),
            nn.ReLU(),

            nn.Linear(128,64),
            nn.BatchNorm1d(64),
            nn.ReLU(),

            nn.Linear(64,32),
            nn.BatchNorm1d(32),
            nn.ReLU(),

            nn.Linear(32,num_classes)
        ) 

    #例如,输入一个2*6的文本序列,表示2个样本,每个样本6个单词

    def forward(self,x):
        #将每个单词都转为词向量
        #例如,输入的x 是2*6的,每个单词用128维表示
        #那么x经过embedding层后,就会变为2*6*128的结果
        x = self.embedding(x)
        #计算一个句子中各个单词的词向量和
        #也就是将每个句子中的单词的词向量相加后,得到每个句子的向量表示
        #例如, 2*6*128的x ，就会被转换为2*128的结果
        #也就是2个句子,每个句子都用128维来表示
        x = torch.sum(x,dim=1)

        x = self.fc(x)

        return x

if __name__ == "__main__":
    model = TextClassifier(
        vocab_size=5000,
        embed_dim=128,
        num_classes=4,
        padding_idx=0
    )                

    #打印模型结构
    print(model)
    #定义一个2*6的输入数据，表示2个样本，每个样本6个单词
    x = torch.randint(0,5000,(2,6))

    print(x)
    output = model(x)

    print(output)
    print(output.shape)    