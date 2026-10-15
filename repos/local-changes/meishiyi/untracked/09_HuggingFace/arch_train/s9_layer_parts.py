"""Q: what is one "layer"? Print Qwen3-0.6B skeleton (meta device, no weights)."""
from pathlib import Path
import torch
from transformers import AutoConfig, AutoModelForCausalLM

cfg = AutoConfig.from_pretrained(Path(__file__).resolve().parent.parent / "models" / "Qwen3-0.6B")
with torch.device("meta"):
    m = AutoModelForCausalLM.from_config(cfg)
print("model.model parts:", [n for n, _ in m.model.named_children()], "| lm_head")
print("len(layers) =", len(m.model.layers))
print("layers[0] parts:", [f"{n}({type(c).__name__})" for n, c in m.model.layers[0].named_children()])
