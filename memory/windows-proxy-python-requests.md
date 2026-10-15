---
name: windows-proxy-python-requests
description: 这台机器开着 VPN 系统代理 127.0.0.1:7890；Python requests 自动读注册表代理而 curl 不读，导致 HuggingFace 下载报错，已用用户级 NO_PROXY 绕过
metadata: 
  node_type: memory
  type: project
  originSessionId: 3c6ba6ae-b1d3-42be-a54d-ade407078a69
  modified: 2026-09-29T10:11:11.934Z
---

这台 Windows 机器常年开着 VPN 客户端的系统代理（注册表 ProxyEnable=1，ProxyServer=127.0.0.1:7890）。
Git Bash 里的 curl **不读**注册表代理（直连），但 Python 的 `requests`/`urllib` 会自动读到它并走代理，
所以"curl 能通、Python 报错"是这台机器的典型假象。

2026-09-20 实际踩到的坑：`huggingface_hub` 经代理访问 hf-mirror.com 拿到的是不带 `X-Repo-Commit` 头的 308，
报 `FileMetadataError: Distant resource does not seem to be on huggingface.co`。
已处理：`setx NO_PROXY "hf-mirror.com,.hf.co"`（用户级），并且 `setx HF_ENDPOINT https://hf-mirror.com`、
`setx HF_HUB_DISABLE_SYMLINKS_WARNING 1`。新开的终端才会生效；当前 shell 里要 `export` 一遍。

**Why:** 用户不希望关 VPN，而 HF 镜像本来就是给直连准备的；绕过代理比切换代理规则更省事、不影响其他项目。

**How to apply:** 以后任何"Python 联网报错但 curl 正常"的问题，先用
`uv run python -c "import urllib.request as u; print(u.getproxies())"` 看 Python 看到的代理，
再决定是把域名加进 NO_PROXY 还是让代理放行。另一个相关坑见 [[bash-chinese-chars-fail]]。
另外：`uvx --from huggingface_hub hf download` 拉的是最新 hub（1.x，httpx + Xet），在这台机器上会卡在 0 字节；
下模型改用项目 venv 里的 `snapshot_download(..., ignore_patterns=['*.h5','*.msgpack','*.ot'])`。

**2026-09-29 更新（情况反过来了）：** 当天直连 hf-mirror.com 和 huggingface.co 都超时（curl `--noproxy '*'` 15 秒无响应），
只有走代理 `-x http://127.0.0.1:7890` 能通。但走代理拉 huggingface.co 的大文件（重定向到 us.gcp.cdn.hf.co）极慢，
20 分钟只到 13 MB 就断；`snapshot_download` 走代理也照样报 `Distant resource does not seem to be on huggingface.co`。
**最快的路是 ModelScope 走代理 + curl**（实测 7.6 MB/s，1.5 GB 三四分钟）：
`curl -sSL -x http://127.0.0.1:7890 --retry 5 -C - -o model.safetensors https://modelscope.cn/models/Qwen/Qwen3-0.6B/resolve/master/model.safetensors`
（这台 curl 不认 `--retry-all-errors`，别加）。小文件（config/tokenizer）从 huggingface.co 走代理也能拿。
Qwen3-0.6B 已下到 `C:\workspace\meishiyi\09_HuggingFace\models\Qwen3-0.6B`，本地 demo 用 `from_pretrained("models/Qwen3-0.6B")` 直接加载。
同日下午 hf-mirror 直连和走代理都 000，ModelScope **直连** curl 就通：逐个文件 `https://www.modelscope.cn/models/<org>/<name>/resolve/master/<file>`，Qwen3-0.6B-Base（1.2 GB）几分钟拉完，已放 `models/Qwen3-0.6B-Base`。
结论：下模型前先用 curl 并行测四条路（mirror 直连/代理、modelscope 直连/代理）各拉 8 MB 看速度，再选。
