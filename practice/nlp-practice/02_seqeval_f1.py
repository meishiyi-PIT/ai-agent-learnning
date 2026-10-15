"""练习 2:实体级 P/R/F1(文档 2.5)—— 先手算,再跑代码对答案

NER 评估的残酷规则:按"整个实体"统计,边界错一个字都算全错。

场景:  小 王 在 杭 州 开 了 家 奶 茶 店
真实:  小王=PER,杭州=LOC(共 2 个实体)
预测:  小王=PER 对了;但把"杭州奶茶店"整体框成了 ORG(边界+类别都错)

先手算(写在纸上再往下看):
    P = 预测对的 / 预测总数 = ?
    R = 预测对的 / 真实总数 = ?
    F1 = 2PR/(P+R)        = ?

运行:  uv run python 02_seqeval_f1.py
"""

from seqeval.metrics import classification_report, f1_score

#         小       王       在   杭       州       开   了   家   奶   茶   店
y_true = [["B-PER", "I-PER", "O", "B-LOC", "I-LOC", "O", "O", "O", "O", "O", "O"]]

# 模型预测:小王对了;"杭州奶茶店"被整体框成 ORG
y_pred = [["B-PER", "I-PER", "O", "B-ORG", "I-ORG", "I-ORG", "I-ORG", "I-ORG", "O", "O", "O"]]

print("实体级 F1:", f1_score(y_true, y_pred))
print(classification_report(y_true, y_pred))

# ---- 校对 ----
# 你手算的 P/R/F1 和上面打印的 micro avg 一致吗?
# 注意看 report 里 LOC 一行(R=0)和 ORG 一行(P=0)——
# 一个"框大了"的错误,会同时污染两个类别的分数。
