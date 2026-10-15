---
name: params-name-and-how-to-tune
description: "讲配置参数时：每条要点都写明是哪个参数（不靠上下文省略主语）；讲完\"影响\"必须接着讲\"怎么调\"（先定约束→按场景给起步值→压测验证），不能只讲调大调小的后果"
metadata:
  node_type: memory
  type: feedback
  originSessionId: c1e4ccc3-1298-408d-9268-4e64ff3f4686
  modified: 2026-09-29T10:01:43.765Z
---

2026-09-29 讲课件 5 第 3.4 节 max_num_seqs / max_num_batched_tokens 时，我把"调大→TTFT 变好、调小→Chunked Prefill"写成子弹，
没写是哪个参数；也只讲了影响、没讲怎么调。用户指出："你没讲 max_num_batched_tokens 怎么调整""你这里没说是哪个参数"。

**Why:** 两个参数并列时省略主语，用户分不清每条说的是谁；只讲"调大调小的后果"等于没教会调参，面试和上手都要"怎么定这个值"。
**How to apply:** 并列讲多个参数时，每条要点开头写参数名；每个可调参数讲完影响后，补"怎么调"三步：硬约束（如 ≥ 另一个参数）→ 按业务场景给起步值（引官方文档原话/数字）→ 压测对照 SLO 调整。能在本机测就跑个小 demo 把取舍量化。关联 [[pacing-small-chunks]]、[[explain-demo-output]]。
