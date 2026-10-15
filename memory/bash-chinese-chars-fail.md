---
name: bash-chinese-chars-fail
description: 这台 Windows 机器上 Bash 工具的命令串里含中文字符会整条以 exit 127 失败；含中文的路径/模式/内容改用 Read/Grep/Edit/Write 工具或先写成脚本文件再运行
metadata: 
  node_type: memory
  type: project
  originSessionId: a18d883d-17aa-4dcd-ad8d-f4d1af9b5b9e
  modified: 2026-09-19T08:56:19.897Z
---

Bash 工具在这台机器（Windows 11 + Git Bash 包装层）上，只要命令文本里出现中文字符（echo 的字符串、grep 的模式、含中文的文件路径、python -c 里的中文），整条命令就会以 exit 127 "No such file or directory" 失败，即使命令本身没问题。纯 ASCII 的命令正常。

**Why:** 2026-09-19 连续三条含中文的命令全部 127 失败，去掉中文后同样的命令立刻成功；multi-line `python -c "..."` 含中文也同样失败。

**How to apply:** 需要中文时——读文件用 Read、搜内容用 Grep、改文件用 Edit/Write；要跑含中文的 Python 逻辑就先用 Write 写成 .py 脚本（放 `C:\Users\meish\AppData\Local\Temp\`），再用纯 ASCII 路径的 Bash 命令运行，用完 rm 掉。中文路径可用通配符绕开（如 `C:/workspace/*/*-Transformer.md`）。
