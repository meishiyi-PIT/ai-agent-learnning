# Transform

## 理解



## 怎么用







## 方法记录

### 1. `unsqueeze` 

是 PyTorch 的张量操作，**在指定维度上插入一个新的维度（大小为 1）**。

简单理解：

```python
x = torch.tensor([1, 2, 3])
print(x.shape)                  # torch.Size([3])

x_unsqueezed = x.unsqueeze(0)  # 在第0维插入
print(x_unsqueezed.shape)       # torch.Size([1, 3])

x_unsqueezed = x.unsqueeze(1)  # 在第1维插入
print(x_unsqueezed.shape)       # torch.Size([3, 1])
```



### 2. `k.size(-1)` 

获取张量 `k` **最后一个维度的大小**。

简单理解：

```python
x = torch.tensor([[[1, 2, 3], [4, 5, 6]]])
print(x.shape)           # torch.Size([1, 2, 3])

x.size(0)   # 第0维: 1
x.size(1)   # 第1维: 2  
x.size(2)   # 第2维: 3
x.size(-1)  # 最后一维: 3 ← 等同于 x.size(2)
x.size(-2)  # 倒数第二维: 2
x.size(-3)  # 倒数第三维: 1
```



### 3. `torch.matmul` 

是 PyTorch 的**矩阵乘法**函数。

简单理解

```python
# 2D矩阵乘法
A = torch.tensor([[1, 2], [3, 4]])      # 形状 [2, 2]
B = torch.tensor([[5, 6], [7, 8]])      # 形状 [2, 2]
C = torch.matmul(A, B)                  # 形状 [2, 2]
# 等价于 C = A @ B

# 高维张量乘法 (批量操作)
A = torch.randn([32, 10, 20])           # [batch, n, m]
B = torch.randn([32, 20, 30])           # [batch, m, p]
C = torch.matmul(A, B)                  # [batch, n, p]
```

规则

- 矩阵形状 `[m, n]` × `[n, p]` → `[m, p]`
- **最后两个维度做乘法**，前面维度保持或广播





# PyTorch 张量操作学习笔记

## 1. 张量维度操作

### `tensor.size()` — 获取张量形状
```python
x = torch.tensor([[[1, 2, 3], [4, 5, 6]]])
print(x.shape)           # torch.Size([1, 2, 3])

x.size(0)    # 第0维: 1
x.size(1)    # 第1维: 2  
x.size(2)    # 第2维: 3
x.size(-1)   # 最后一维: 3 (等同于 x.size(2))
x.size(-2)   # 倒数第二维: 2
```

**关键点**：
- 负索引从后往前数：`-1` 是最后一维，`-2` 是倒数第二维
- 这样写代码更灵活，不硬编码维度数

### `tensor.unsqueeze(dim)` — 插入维度
```python
x = torch.tensor([1, 2, 3])           # [3]
x.unsqueeze(0)                         # [1, 3]
x.unsqueeze(1)                         # [3, 1]

# 在多维张量中
y = torch.tensor([[1, 2], [3, 4]])    # [2, 2]
y.unsqueeze(1)                         # [2, 1, 2]
y.unsqueeze(-1)                        # [2, 2, 1]
```

**应用场景**：为广播做准备，扩展维度以匹配后续操作

### `tensor.squeeze(dim)` — 移除大小为1的维度
```python
x = torch.tensor([[[1, 2, 3]]])       # [1, 1, 3]
x.squeeze(0)                           # [1, 3]
x.squeeze(1)                           # [1, 1, 3] 不变（该维度大小不是1）
```

---

## 2. 张量运算

### `torch.matmul()` — 矩阵乘法
```python
# 基本规则：[m, n] × [n, p] → [m, p]
A = torch.tensor([[1, 2], [3, 4]])    # [2, 2]
B = torch.tensor([[5, 6], [7, 8]])    # [2, 2]
C = torch.matmul(A, B)                # [2, 2]
# 简写：C = A @ B

# 高维张量（批量操作）— 最后两个维度做乘法
A = torch.randn([batch, seq_len, d_k])        # [32, 10, 64]
B = torch.randn([batch, d_k, seq_len])        # [32, 64, 10]
C = torch.matmul(A, B)                        # [32, 10, 10]
```

**应用场景**：注意力机制中计算 Query × Key^T

### `tensor.transpose(dim1, dim2)` — 交换两个维度
```python
x = torch.randn([batch, seq_len, d_k])       # [2, 10, 64]
x.transpose(-2, -1)                          # [2, 64, 10]
x.transpose(1, 2)  # 等效写法

# 可用于矩阵转置
x.t()  # 等同于 x.transpose(-2, -1) 的快捷方式
```

---

## 3. 元素级运算（运算符重载）

### 比较运算
```python
x = torch.tensor([1, 2, 0, 3])
padding_idx = 0

# 逐元素比较，返回布尔张量
mask = (x == padding_idx)              # tensor([False, False, True, False])
mask = (x != padding_idx)              # tensor([True, True, False, True])
mask = (x < 2)                         # tensor([True, False, True, False])
```

**不是 Python 原生语法**：
- Python 列表：`[1, 2, 0] == 0` 会报错
- PyTorch 张量：`torch.tensor([1, 2, 0]) == 0` 返回逐元素比较结果
- **实现原理**：PyTorch 通过重载 `__eq__`、`__lt__` 等方法实现

### 常见的运算符重载
```python
x = torch.tensor([1, 2, 3])
y = torch.tensor([2, 2, 2])

x + y      # 逐元素相加        → __add__
x - y      # 逐元素相减        → __sub__
x * y      # 逐元素相乘        → __mul__
x / y      # 逐元素相除        → __truediv__
x @ y      # 矩阵乘法          → __matmul__
x == y     # 逐元素比较        → __eq__
```

---

## 4. 实战应用：Transformer 注意力机制

### 位置编码中的 unsqueeze
```python
position = torch.arange(0, max_len)          # [max_len]
position = position.unsqueeze(1)             # [max_len, 1]
div_term = torch.arange(0, d_model, 2)       # [d_model/2]

# 通过广播，形状变为 [max_len, d_model/2]
pe = torch.sin(position * div_term)

pe = pe.unsqueeze(0)                         # [1, max_len, d_model/2]
```

### Padding 掩码中的运算符重载
```python
def get_padding_mask(x, padding_idx):
    # 逐元素比较：哪些是 padding
    comparison = (x == padding_idx)            # [batch, seq_len] 的布尔张量
    return comparison.unsqueeze(1)             # [batch, 1, seq_len]
```

### 注意力分数计算
```python
def attention(q, k, v, mask=None, dropout=None):
    d_k = k.size(-1)                          # 获取每个 head 的维度
    
    # k.transpose(-2, -1)：[batch, heads, seq_len, d_k] 
    #                  → [batch, heads, d_k, seq_len]
    scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(d_k)
    # 形状：[batch, heads, seq_len_q, seq_len_k]
    
    if mask is not None:
        scores = scores.masked_fill(mask, -1e9)  # 将 True 位置填为极小值
    
    p_attn = torch.softmax(scores, dim=-1)
    return torch.matmul(p_attn, v)
```

---

## 5. 维度索引速查表

| 操作 | 语法 | 含义 |
|------|------|------|
| 获取维度大小 | `x.size(0)` | 第1个维度 |
| | `x.size(-1)` | 最后一个维度 |
| 添加维度 | `x.unsqueeze(0)` | 在开头添加维度 |
| | `x.unsqueeze(-1)` | 在末尾添加维度 |
| 移除维度 | `x.squeeze(0)` | 移除第1个维度（如果大小为1） |
| 交换维度 | `x.transpose(-2, -1)` | 交换最后两个维度 |
| 形状变换 | `x.reshape(new_shape)` | 重塑张量（不改变数据） |
| 展平 | `x.flatten()` | 展成1D |

---

## 6. 关键概念总结

### 广播（Broadcasting）
```python
# 自动对齐维度进行运算
a = torch.tensor([[1], [2], [3]])     # [3, 1]
b = torch.tensor([10, 20, 30])        # [3]
c = a + b                              # [3, 3]
```

### 运算符重载 vs 函数调用
```python
# 等价的两种写法
result1 = x == 0              # 运算符重载（更直观）
result2 = torch.eq(x, 0)      # 函数调用（功能相同）

result1 = x @ y               # 矩阵乘法
result2 = torch.matmul(x, y)  # 等价
```

### 负索引的妙用
```python
# 不管张量有几个维度，都能引用最后几个维度
x.size(-1)        # 总是最后一维
x.transpose(-2,-1) # 总是交换最后两维
x.view(-1, 1)     # -1 表示自动推导维度大小
```