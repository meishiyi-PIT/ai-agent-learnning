"""
课件 5《大模型推理部署》第 4 节追问：s14 里的 18 个 token 是什么？第 ⑧ 站为什么不能只解码当前 token？

运行（在 meishiyi/09_HuggingFace 目录下，只加载分词器，几秒）：
    .venv/Scripts/python -X utf8 inference_deploy/s15_tokens_detok.py

第一段：把 s14 的输入 18 个 token 逐个解码出来看——问题本身只占几个，其余是对话模板加的标记。
第二段：有的字会被拆成好几个 token（Qwen 的分词器按字节切，生僻字、emoji 常见），
       每个 token 单独解码只是半个字，得到乱码"�"；凑齐了一起解码才是完整的字。
       所以第 ⑧ 站每步虽然只多了 1 个 token，却要"全部编号一起解码、切掉已输出的前缀"，
       结尾是"�"（字还没凑齐）就先不输出，等下一步。vLLM 的增量 Detokenizer 也是这么做的。

Python 语法点：
- `[tokenizer.decode([i]) for i in ids]`：列表推导式，每个编号单独解码成文字。
- `repr(s)`：带引号、把换行显示成 \\n，方便看清空白字符。
"""
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("models/Qwen3-0.6B")

# ---- 第一段：18 个输入 token ----
text = tokenizer.apply_chat_template(
    [{"role": "user", "content": "用两句话介绍长城。"}], tokenize=False,
    add_generation_prompt=True, enable_thinking=False,
)
ids = tokenizer(text)["input_ids"]
print(f"输入 {len(ids)} 个 token：{[tokenizer.decode([i]) for i in ids]}")

# ---- 第二段：一个字被拆成几个 token ----
def pieces(w):
    return [tokenizer.decode([i]) for i in tokenizer(w, add_special_tokens=False)["input_ids"]]


# 常用字和常见 emoji 在词表里是整字；从一串生僻字 / 新 emoji 里挑第一个会被拆开的
word = next(w for w in ["齉", "龘", "𪚥", "𠀀", "🫠", "🪿"] if any("�" in p for p in pieces(w)))
wids = tokenizer(word, add_special_tokens=False)["input_ids"]
print(f"'{word}' 被拆成 {len(wids)} 个 token，逐个单独解码：{[tokenizer.decode([i]) for i in wids]}")

shown, steps = "", []
for k in range(1, len(wids) + 1):
    full = tokenizer.decode(wids[:k])
    if full.endswith("�"):        # 结尾是半个字，先不输出
        steps.append("（先不出）")
        continue
    steps.append(repr(full[len(shown):]))
    shown = full
print(f"增量解码每一步推给用户的：{steps}")
