"""练习 1:NER 标签对齐(文档 3.2,全文唯一的硬核难点)—— 默写练习

背景(为什么需要对齐):
    NER 数据是"按字/词"标注的,但 tokenizer 可能把一个词拆成多个 token,
    还会在句子前后插入 [CLS]/[SEP] 特殊符号。
    于是"标签数量"和"token 数量"对不上,必须重新对齐:
      - token 属于第 i 个原词 -> 照抄原词的标签
      - token 是 [CLS]/[SEP]/padding(word_ids 里是 None)-> 填 -100
    -100 的含义:PyTorch 交叉熵损失默认 ignore_index=-100,
    贴了 -100 的位置不参与损失计算。

本练习不联网、不加载真模型:用 FakeTokenized 模拟 tokenizer 的行为,
你只需要默写核心对齐逻辑(文档里的 process_function 内层循环)。

运行:  uv run python 01_label_align.py
通过标准:两个 assert 都不报错。
"""

label_list = ["O", "B-PER", "I-PER", "B-ORG", "I-ORG", "B-LOC", "I-LOC"]


class FakeTokenized:
    """模拟 tokenizer(...) 的返回对象,只实现 word_ids() 一个方法。

    场景:原始 tokens = ['小', '王', '在', '杭', '州']
    tokenizer 编码后实际的 token 序列是:
        [CLS]  小  王  在  杭  州  [SEP]
    word_ids() 告诉你每个 token 回溯到第几个原始词(特殊符号是 None):
    """

    def word_ids(self):
        return [None, 0, 1, 2, 3, 4, None]


def align_labels(word_ids: list, ner_tags: list) -> list:
    """把"按词"的标签 ner_tags 翻译成"按 token"的标签列表。

    参数:
        word_ids: 如 [None, 0, 1, 2, 3, 4, None]
        ner_tags: 如 [1, 2, 0, 5, 6]  (即 B-PER I-PER O B-LOC I-LOC)
    返回:
        与 word_ids 等长的标签 id 列表
    """
    label_ids = []
    for word_id in word_ids:
        if word_id is None:
            # [CLS]/[SEP]/padding:填 -100,交叉熵损失自动忽略
            label_ids.append(-100)
        else:
            # 普通 token:照抄它所属原词的标签
            label_ids.append(ner_tags[word_id])
    return label_ids


if __name__ == "__main__":
    # 小王在杭州:小王=人名(B-PER,I-PER),杭州=地名(B-LOC,I-LOC)
    ner_tags = [1, 2, 0, 5, 6]
    result = align_labels(FakeTokenized().word_ids(), ner_tags)

    print("对齐结果:", result)
    print("可读版本:", [label_list[i] if i != -100 else "IGN" for i in result])

    assert len(result) == 7, "输出长度必须等于 token 数(含 CLS/SEP)"
    assert result == [-100, 1, 2, 0, 5, 6, -100], "对齐结果不对,回看文档 3.2 流程图"
    print("PASS ✓")

    # ---- 费曼收尾(口头回答,不用写代码)----
    # Q1: 如果把 None 位置填 0("O")而不是 -100,训练时会发生什么坏事?
    # Q2: 英文场景 knowledge 被拆成 know+ledge 两个 token 时,
    #     word_ids 会长什么样?本函数还能正确工作吗?
