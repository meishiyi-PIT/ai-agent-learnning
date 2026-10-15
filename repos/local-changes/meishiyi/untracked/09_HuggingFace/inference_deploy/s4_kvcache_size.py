"""
课件 5《大模型推理部署》第四部分第 4 节：KV Cache 要占多少显存

运行（在 meishiyi/09_HuggingFace 目录下，CPU 即可）：
    .venv/Scripts/python -X utf8 inference_deploy/s4_kvcache_size.py

公式（每个请求）：
    KV Cache 字节数 = 2（K 和 V 两份）× 层数 × KV 头数 × 头维度 × 序列长度 × 每个数的字节数
前四项都在模型的 config.json 里：num_hidden_layers / num_key_value_heads / head_dim / torch_dtype。

第一段：Qwen3-0.6B 真跑一次 Prefill，把缓存里每层 K、V 张量的字节数加起来，和公式对账。
第二段：用公式算课件表格里那几类模型在 4K / 32K / 128K 上下文下的缓存大小（BF16）。

课件勘误（教到这里时说）：
- 表格标的是 BF16（2 字节），但数字是按 4 字节算的，整体大了一倍；
  "Qwen3-7B（GQA 4 头）"这一行的数又是按 8 个 KV 头算的；而且 Qwen3 没有 7B，28 层 + 4 个 KV 头 + 128 维是 Qwen2.5-7B。
- "传统 MHA 约 0.7 MB / token"：LLaMA-7B 按 BF16 实际是 0.5 MB / token。

Python 语法点：
- `t.nelement() * t.element_size()`：张量的元素个数 × 每个元素的字节数 = 张量占多少字节。
- `sum(... for ... in ...)`：生成器表达式求和，等于 Java 里 stream().mapToLong(...).sum()。
"""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def kv_bytes(layers, kv_heads, head_dim, seq_len, bytes_per_elem=2):
    return 2 * layers * kv_heads * head_dim * seq_len * bytes_per_elem


# ============ 第一段：真实缓存 vs 公式 ============
MODEL_DIR = "models/Qwen3-0.6B"
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
# 用 BF16 加载，缓存也是 BF16（每个数 2 字节），和公式的假设一致
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.bfloat16)
model.eval()

text = "The Great Wall of China is a series of fortifications. " * 60
ids = tokenizer(text, return_tensors="pt")
seq_len = ids["input_ids"].shape[1]
with torch.no_grad():
    cache = model(**ids, use_cache=True).past_key_values

measured = sum(t.nelement() * t.element_size() for t in cache.key_cache + cache.value_cache)
cfg = model.config
formula = kv_bytes(cfg.num_hidden_layers, cfg.num_key_value_heads, cfg.head_dim, seq_len)
print(f"Qwen3-0.6B 输入 {seq_len} 个 token：实测缓存 {measured / 1e6:.1f} MB，"
      f"公式 {formula / 1e6:.1f} MB，每个 token {formula / seq_len / 1e3:.0f} KB")

# ============ 第二段：课件表格里的模型，按 BF16 重算 ============
models = [
    ("Qwen2.5-7B  28层 4个KV头", 28, 4, 128),
    ("Qwen3-8B    36层 8个KV头", 36, 8, 128),
    ("LLaMA-2-7B  32层 32个KV头", 32, 32, 128),
]
for name, layers, kv_heads, head_dim in models:
    per_tok = kv_bytes(layers, kv_heads, head_dim, 1)
    cells = "  ".join(f"{L // 1024}K={kv_bytes(layers, kv_heads, head_dim, L) / 1e9:5.1f}GB"
                      for L in (4096, 32768, 131072))
    print(f"{name}: 每 token {per_tok / 1e3:4.0f} KB  {cells}")
