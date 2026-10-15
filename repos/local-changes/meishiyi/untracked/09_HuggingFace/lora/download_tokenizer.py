"""
第 4 站准备：只下载 DeepSeek-R1-Distill-Qwen-1.5B 的 tokenizer 文件（几 MB），不下模型权重。
1.5B 和课件用的 7B 共用同一套 tokenizer / chat_template，足以复现课件 4.3 的数据处理流程。

运行（在 meishiyi/09_HuggingFace 目录）：
    PYTHONUTF8=1 uv run python lora/download_tokenizer.py
"""

import os
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from huggingface_hub import snapshot_download

target = Path(__file__).resolve().parent.parent / "models" / "deepseek-r1-distill-qwen-tokenizer"
path = snapshot_download(
    repo_id="deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
    allow_patterns=["tokenizer.json", "tokenizer_config.json", "config.json", "generation_config.json"],
    local_dir=str(target),
)
print("saved to:", path)
for f in sorted(Path(path).iterdir()):
    print(f"  {f.name:28s} {f.stat().st_size / 1024:.0f} KB")
