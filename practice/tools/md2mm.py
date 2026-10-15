"""
把 Markdown 大纲转成 FreeMind .mm 文件（ProcessOn / XMind / FreeMind 都能直接导入）。

规则：
  - `#`、`##`、`###` … 标题 → 第 1、2、3 … 层节点
  - 标题下面的 `-` 列表 → 继续往下挂，每缩进 2 个空格深一层
  - 去掉 **加粗**、`代码` 的标记符号，$公式$ 保留内容去掉美元号
  - 空行、代码块、引用块、表格行忽略

用法：
  python tools/md2mm.py <输入.md> <输出.mm>
"""
import re
import sys
from xml.sax.saxutils import quoteattr


def clean(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\$(.+?)\$", r"\1", text)
    return text


def parse(lines):
    """返回 (depth, text) 列表；depth 从 1 开始。"""
    items = []
    heading_depth = 0
    in_code = False
    for raw in lines:
        line = raw.rstrip("\n")
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or not line.strip():
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            heading_depth = len(m.group(1))
            items.append((heading_depth, clean(m.group(2))))
            continue
        m = re.match(r"^(\s*)[-*+]\s+(.*)$", line)
        if m:
            indent = len(m.group(1).replace("\t", "  "))
            depth = heading_depth + 1 + indent // 2
            items.append((depth, clean(m.group(2))))
            continue
        # 其它行（段落/表格/引用）忽略
    return items


def build(items):
    root_depth, root_text = items[0]
    out = ['<map version="1.0.1">']
    stack = [root_depth]
    out.append(f"<node TEXT={quoteattr(root_text)}>")
    for depth, text in items[1:]:
        if depth > stack[-1] + 1:
            depth = stack[-1] + 1  # 防止跳级
        while stack and depth <= stack[-1]:
            out.append("</node>")
            stack.pop()
        out.append(f"<node TEXT={quoteattr(text)}>")
        stack.append(depth)
    while stack:
        out.append("</node>")
        stack.pop()
    out.append("</map>")
    return "\n".join(out)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        items = parse(f.readlines())
    xml = build(items)
    with open(dst, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + xml)
    print(f"{len(items)} nodes -> {dst}")


if __name__ == "__main__":
    main()
