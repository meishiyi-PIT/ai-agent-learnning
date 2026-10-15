"""
课件 5《大模型推理部署》PagedAttention 第 2 节：前缀共享与 Copy-on-Write（写时复制）

运行（纯 Python，不需要 torch）：
    .venv/Scripts/python -X utf8 inference_deploy/s9_cow.py

接着 s8 的块管理，加一样东西：引用计数（每个物理块现在被几张 Block Table 指着）。
场景：并行采样 n=2，同一个 prompt 要两个不同的回答。
- 分叉：两个样本的表都指向 prompt 的那几块，不复制，引用计数 +1；
- 写时复制：要往一个被共用（计数 > 1）的块里写新 token 时，先复制一份给自己、计数 -1，再写；
  如果块只剩自己在用（计数 = 1），直接写，不用复制。
写满的块永远不会再被写，所以一直共用；只有最后那个没写满的块才可能被复制。

课件勘误：课件说"论文实测共享场景能省下约 55~67% 的 KV 内存"，这只是 beam search 的上限。
vLLM 论文 6.3 节原文：并行采样省 6.1%~9.8%（Alpaca）/ 16.2%~30.5%（ShareGPT），
beam search 省 37.6%~55.2%（Alpaca）/ 44.3%~66.3%（ShareGPT）。

Python 语法点：
- `dict(ref)`：复制一份字典再打印，避免打印的是后面被改过的同一个对象。
- `physical[new] = list(physical[old])`：`list(...)` 复制一份新列表；直接 `= physical[old]` 两个名字指向同一个列表，改一个另一个也变。
"""
BLOCK = 4
physical = [[None] * BLOCK for _ in range(4)]
free = [0, 1, 2, 3]
ref = {}   # 物理块号 → 被几张表指着


def alloc():
    b = free.pop(0)
    ref[b] = 1
    return b


class Seq:
    def __init__(self, table=None, n=0):
        self.table = table or []
        self.n = n

    def fork(self):
        for b in self.table:
            ref[b] += 1
        return Seq(list(self.table), self.n)

    def append(self, tok):
        logical, slot = divmod(self.n, BLOCK)
        if slot == 0:
            self.table.append(alloc())
        else:
            old = self.table[logical]
            if ref[old] > 1:              # 块被共用：先复制一份给自己
                new = alloc()
                physical[new] = list(physical[old])
                ref[old] -= 1
                self.table[logical] = new
        physical[self.table[logical]][slot] = tok
        self.n += 1

    def read(self):
        return "".join(physical[self.table[i // BLOCK]][i % BLOCK] for i in range(self.n))


prompt = Seq()
for t in ["中国", "的", "历史", "非常", "悠久"]:
    prompt.append(t)
s1, s2 = prompt, prompt.fork()
print(f"分叉后：样本1 的表 {s1.table}，样本2 的表 {s2.table}，引用计数 {dict(ref)}")

s1.append("，")
print(f"样本1 写'，'：块1 被两人共用 → 复制成块2 再写；样本1 的表 {s1.table}，引用计数 {dict(ref)}")
s2.append("而")
print(f"样本2 写'而'：块1 只剩它在用 → 直接写；样本2 的表 {s2.table}")
print(f"读回：样本1 = {s1.read()}   样本2 = {s2.read()}")
print(f"不共用要 4 块，共用后实际用了 {len(ref)} 块（块0 一直两人共用）")
