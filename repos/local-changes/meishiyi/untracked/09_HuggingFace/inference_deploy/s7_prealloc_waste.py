"""
课件 5《大模型推理部署》PagedAttention 第 1 节：朴素 Serving 预分配浪费多少显存

运行（纯 Python，不需要 torch）：
    .venv/Scripts/python -X utf8 inference_deploy/s7_prealloc_waste.py

接着 s5 的账：一张 4090 跑 DeepSeek-R1-Distill-Qwen-7B，缓存池 5.0 GB，每 token 57 KB。
来 40 个请求，每个实际用的 token 数（输入 + 输出）在 200~2000 之间随机。
- 朴素做法：每个请求按 max_model_len=8192 预留一整段连续空间，不管它实际用多少；
- 按块分配：每 16 个 token 一块，用到哪块才领哪块，只有每个请求的最后一块可能没填满。
比两件事：池子能同时放下几个请求、放进去的空间有几成真的存了 K、V。

Python 语法点：
- `random.seed(0)`：固定随机种子，每次跑出同样的请求长度，方便对照。
- `-(-n // 16)`：向上取整的整数写法（n 个 token 要几块），等于 math.ceil(n / 16)。
"""
import random

KV_PER_TOKEN = 2 * 28 * 4 * 128 * 2          # 57,344 字节，同 s5
POOL_TOKENS = int(5.0e9 / KV_PER_TOKEN)      # 缓存池能装的 token 数
MAX_MODEL_LEN = 8192
BLOCK = 16

random.seed(0)
lens = [random.randint(200, 2000) for _ in range(40)]


def admit(cost_of):
    """按到达顺序往池子里放请求，放不下就停；返回放进去的请求和占掉的 token 位。"""
    used, taken = [], 0
    for n in lens:
        if taken + cost_of(n) > POOL_TOKENS:
            break
        used.append(n)
        taken += cost_of(n)
    return used, taken


naive, naive_taken = admit(lambda n: MAX_MODEL_LEN)
paged, paged_taken = admit(lambda n: -(-n // BLOCK) * BLOCK)

print(f"缓存池 {POOL_TOKENS} 个 token 位；40 个请求实际平均用 {sum(lens) / len(lens):.0f} 个")
print(f"朴素预分配 8192：同时放下 {len(naive):2d} 个，占掉的位置里真存了 K、V 的 {sum(naive) / naive_taken:5.1%}")
print(f"按 16 个一块  ：同时放下 {len(paged):2d} 个，占掉的位置里真存了 K、V 的 {sum(paged) / paged_taken:5.1%}")
