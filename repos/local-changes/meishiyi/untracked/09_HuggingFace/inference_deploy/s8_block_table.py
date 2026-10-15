"""
课件 5《大模型推理部署》PagedAttention 第 2 节：Block Table 一次完整的读写流程

运行（纯 Python，不需要 torch）：
    .venv/Scripts/python -X utf8 inference_deploy/s8_block_table.py

用几十行 Python 模拟 vLLM 的块管理（真实 vLLM 每块 16 个 token，这里用 4 个方便看）：
- 物理块：显存里一格一格大小相同的小块，每格放 4 个 token 的 K、V（这里直接放 token 文字代替 K、V）；
- Block Table：每个请求一张表，第 i 行 = 我的第 i 个逻辑块放在几号物理块；
- 写：当前块还有空位就写进去；写满了就从空闲列表里随便领一块，把块号追加到表里；
- 读：注意力计算时按表的顺序一块块找过去，拼回连续的序列；
- 请求结束：把块号还回空闲列表，下一个请求直接领，不要求相邻。

场景：显存一共 4 个物理块。A、B 两个请求交替写，A 的块在物理上不连续；
4 块用完后 B 结束，空出来的块马上给新请求 C。

Python 语法点：
- `self.n % BLOCK == 0`：已写 token 数是 4 的倍数 → 当前块刚好写满（或还没有块），要领新块。
- `divmod(i, BLOCK)`：一次拿到商和余数，即"第几个逻辑块、块里第几格"。
"""
BLOCK = 4
NUM_BLOCKS = 4

physical = [[None] * BLOCK for _ in range(NUM_BLOCKS)]   # 显存：一共 4 个物理块
free = list(range(NUM_BLOCKS))                           # 空闲块号列表


class Request:
    def __init__(self, name):
        self.name = name
        self.table = []   # Block Table：逻辑块号 → 物理块号
        self.n = 0        # 已写入的 token 数

    def append(self, tok):
        if self.n % BLOCK == 0:
            self.table.append(free.pop(0))
        logical, slot = divmod(self.n, BLOCK)
        physical[self.table[logical]][slot] = tok
        self.n += 1

    def read(self):
        return "".join(physical[self.table[i // BLOCK]][i % BLOCK] for i in range(self.n))

    def finish(self):
        free.extend(self.table)
        self.table = []


def show(block_id):
    return "[" + " ".join(t or "_" for t in physical[block_id]) + "]"


A, B = Request("A"), Request("B")
for t in ["中国", "的", "历史", "非常", "悠久"]:
    A.append(t)
for t in ["今天", "天气", "好"]:
    B.append(t)
print(f"A、B 预填充后：A 的表 {A.table}，B 的表 {B.table}；物理块0={show(0)} 物理块1={show(1)}")

for t in ["，", "有", "五千", "年"]:   # A 继续 Decode 4 步
    A.append(t)
print(f"A 又写 4 个 token 后：A 的表 {A.table}，物理块1={show(1)} 物理块3={show(3)}")
print(f"注意力按表读回 A：{A.read()}")

print(f"此时空闲列表 {free}（4 个块全被占了，再来请求只能等）")
returned = list(B.table)
B.finish()
C = Request("C")
C.append("你好")
print(f"B 结束还回块 {returned} → 新请求 C 的表 {C.table}")
