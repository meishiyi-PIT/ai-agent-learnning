"""
课件 5《大模型推理部署》第 3 节 3.3：连续批处理 vs 静态批处理（调度模拟）

运行（纯 Python，不需要 torch）：
    .venv/Scripts/python -X utf8 inference_deploy/s11_continuous_batch.py

不跑模型，只模拟调度：6 个请求一开始就全到了，每个要写的 token 数已知（前 3 个用 s10 实测的 22 / 18 / 372）；
GPU 一步最多同时跑 3 个请求（相当于 vLLM 的 max_num_seqs=3），每步每个在跑的请求写 1 个 token。
- 静态：3 个一批，整批等最长那条写完才放下一批进来；
- 连续：每跑完一步，写完的立刻移出，等待队列里的立刻补进空位（课件 3.3.2 的"组批 → 执行 → 结算"）。
比：全部做完用了几步、每个请求平均第几步拿到结果、多少个位置在空转。

Python 语法点：
- `collections.deque`：双端队列，`popleft()` 从头部取，适合做先来先服务的等待队列。
- `running = [r for r in running if ...]`：列表推导式过滤，只留下还没写完的请求。
"""
from collections import deque

LENS = [22, 18, 372, 30, 25, 200]
MAX_SEQS = 3


def static():
    done, step, busy = {}, 0, 0
    for i in range(0, len(LENS), MAX_SEQS):
        batch = range(i, min(i + MAX_SEQS, len(LENS)))
        longest = max(LENS[j] for j in batch)
        for j in batch:
            done[j] = step + longest      # 短的也要等最长那条
            busy += LENS[j]
        step += longest
    return step, done, MAX_SEQS * step - busy


def continuous():
    waiting = deque(range(len(LENS)))
    running, left, done, step, idle = [], {}, {}, 0, 0
    while waiting or running:
        while waiting and len(running) < MAX_SEQS:   # 组批：有空位就补
            r = waiting.popleft()
            running.append(r)
            left[r] = LENS[r]
        step += 1                                     # 执行：每个在跑的写 1 个 token
        idle += MAX_SEQS - len(running)
        for r in running:
            left[r] -= 1
            if left[r] == 0:
                done[r] = step
        running = [r for r in running if left[r] > 0]  # 结算：写完的移出
    return step, done, idle


for name, (steps, done, idle), label in [("静态", static(), "陪跑白算"), ("连续", continuous(), "空位（队列空了没人可补）")]:
    avg = sum(done.values()) / len(done)
    print(f"{name}：全部做完 {steps:3d} 步；各请求在第 {[done[i] for i in range(len(LENS))]} 步拿到结果，"
          f"平均第 {avg:5.1f} 步；{label} {idle} 个")
