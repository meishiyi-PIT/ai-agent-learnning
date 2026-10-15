"""
更新复习总纲：把某一节的"公式/结论"和"代码流程"两块勾上，并追加进度锚点。
用法：python tools/tick_review.py <节号如 1.1> "<锚点文字>"
"""
import sys

P = r"C:\workspace\学习笔记\大模型底层原理复习\复习-模块五六-总纲.md"


def main():
    sec_no, anchor = sys.argv[1], sys.argv[2]
    s = open(P, encoding="utf-8").read()
    start = s.index(f"### {sec_no} ")
    nxt = s.find("\n### ", start + 1)
    end = nxt if nxt != -1 else s.index("\n## 2.")
    lines = s[start:end].split("\n")
    out, mode = [], None
    for l in lines:
        if "**公式" in l:
            mode = "f"
        elif "**代码" in l:
            mode = "c"
        elif "**GPU" in l:
            mode = "g"
        if mode in ("f", "c") and l.strip().startswith("- [ ]"):
            l = l.replace("- [ ]", "- [x]", 1)
        out.append(l)
    s = s[:start] + "\n".join(out) + s[end:]
    s = s.rstrip("\n") + "\n" + anchor + "\n"
    open(P, "w", encoding="utf-8").write(s)
    print("ticked", sec_no)


if __name__ == "__main__":
    main()
