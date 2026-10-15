"""
一键生成复习知识地图的 .mm 文件（ProcessOn → 导入 → FreeMind）。
运行：python tools/build_review_map.py
（路径含中文，所以不在 Bash 里直接传参，写死在这里。）
"""
import os
import subprocess
import sys

NOTES = r"C:\workspace\学习笔记\大模型底层原理复习"
SRC = os.path.join(NOTES, "复习-模块五六-知识地图.md")
DST = os.path.join(NOTES, "复习-模块五六-知识地图.mm")
HERE = os.path.dirname(os.path.abspath(__file__))

# 三份子任务提取的全量大纲，改成正式名字留档
RENAMES = {
    "_tmp_outline_m5.md": "知识点全量清单-模块五(自动提取).md",
    "_tmp_outline_m6a.md": "知识点全量清单-模块六上-LoRA量化分布式数据集(自动提取).md",
    "_tmp_outline_m6b.md": "知识点全量清单-模块六下-部署架构模块详解(自动提取).md",
}

for old, new in RENAMES.items():
    o, n = os.path.join(NOTES, old), os.path.join(NOTES, new)
    if os.path.exists(o):
        os.replace(o, n)
        print("renamed ->", new)

subprocess.run([sys.executable, os.path.join(HERE, "md2mm.py"), SRC, DST], check=True)
