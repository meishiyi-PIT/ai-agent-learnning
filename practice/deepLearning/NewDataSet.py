from torch.utils.data import Dataset
from torchtext.data.utils import get_tokenizer
import pandas as pd
from torchtext.vocab import build_vocab_from_iterator
from torch.nn.utils.rnn import pad_sequence
import torch

def collate_batch(batch,text_vocab):
    text_list = list()
    labels = list()

    for text,label in batch:
        text_tokens = [text_vocab[token] for token in text]
        text_tensor = torch.tensor(text_tokens,dtype=torch.long)
        text_list.append(text_tensor)
        labels.append(torch.tensor(label-1,dtype=torch.long))

    padding_idx = text_vocab['<pad>']
    text_padded = pad_sequence(text_list,batch_first=True,padding_value=padding_idx)
    lables_tensor=torch.stack(labels)
    return text_padded,lables_tensor
        
def build_vocab(dataset):
    special = ['<unk>','<pad>']
    text_iter = map(lambda x:x[0],dataset)

    text_vocab = build_vocab_from_iterator(text_iter,min_freq=2,specials=special)
    text_vocab.set_default_index(text_vocab['<unk>'])
    return text_vocab

class NewsDataset(Dataset):
    # data对象中保存了原始数据,包括标签label和新闻描述text
    # data[0] = (3,"Wall St. Bears Claw Back Into the ...")
    def __init__(self,is_train=True) -> None:
        super().__init__()
        if is_train:
            data = pd.read_csv("./text_cls/data/ag_news_csv/train.csv")
        else:
            data = pd.read_csv("./text_cls/data/ag_news_csv/test.csv")
        self.examples = list()

        # 返回一个内置的英语分词器
        tokenizer = get_tokenizer("basic_english")
        for index,row in data.iterrows():
            label = row.iloc[0]
            text = row.iloc[2]

            #将文本转成小写，并使用tokenizer进行分词
            tokenized_text = [token.lower() for token in tokenizer(text)]
            #将处理好的文本和标签，保存到list中
            self.examples.append((tokenized_text,label))

    def __len__(self):
        return len(self.examples)
    def __getitem__(self,index):
        return self.examples[index]

if __name__ =="__main__":
    dataset = NewsDataset()
    print(len(dataset))
    print(dataset[0])             