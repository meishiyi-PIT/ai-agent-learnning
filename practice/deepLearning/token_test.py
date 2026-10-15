import torch
import torch.nn as nn

embedding = nn.Embedding(num_embeddings=5,embedding_dim=3)

print("权重矩阵：")
print(embedding.weight.data)

input_indices = torch.tensor([0,2,4])

output = embedding(input_indices)
print("embedding 输出：")
print(output)
