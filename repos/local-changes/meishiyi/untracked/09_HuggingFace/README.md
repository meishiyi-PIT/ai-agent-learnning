# 09_HuggingFace —— 模块五《6.HuggingFace 实战指南》配套练习

课件：`AI大模型应用开发/模块五：AI底层算法原理/6.HuggingFace实战指南.md`
下一份《7.中文NLP实战：情感分类与NER》直接建立在这套环境上。

## 怎么跑

```bash
cd C:/workspace/meishiyi/09_HuggingFace
uv sync                                   # 首次/依赖变更后
PYTHONUTF8=1 uv run python 00_check_env.py   # 环境自检，全绿再开始
PYTHONUTF8=1 uv run python <脚本名>.py       # 跑任意练习脚本
```

`PYTHONUTF8=1` 是 Windows 下防中文输出乱码/报错的保险，习惯性带上。

## 本机环境与课件的差异（读课件时对照）

| 课件写法 | 本机实际 | 原因 |
| --- | --- | --- |
| `pip install ... -i 清华镜像` | `uv sync`（版本号与课件 1.4 完全一致，见 `pyproject.toml`） | 统一用 uv 管环境 |
| `export HF_ENDPOINT=https://hf-mirror.com` | 已写入 Windows **用户级**环境变量，任何新开的终端/IDE 自动生效 | 免得每次手敲；撤销：`setx HF_ENDPOINT ""` |
| （课件没提）系统代理 | 已写入用户级 `NO_PROXY=hf-mirror.com,.hf.co` | 这台机器开着 VPN 系统代理（127.0.0.1:7890）。Python 的 `requests` 会自动读 Windows 注册表代理，经代理访问 hf-mirror 会拿到一个不带 `X-Repo-Commit` 头的 308，`huggingface_hub` 就报 "Distant resource does not seem to be on huggingface.co"。让 HF 这两个域名绕过代理即可，VPN 本身不用关 |
| `huggingface-cli download 模型名 --local-dir 路径` | 两个模型已转成 safetensors 放在本目录 `models/` 下，代码里 **model_id 写本地路径**：`"./models/chinese-macbert-base"`、`"./models/roberta-base-finetuned-dianping-chinese"` | 课件 2.3/2.5/3.2/4.3 写的是 Hub id，换成本地路径即可，其余一字不改。**为什么不用 Hub id**：这两个仓库只有老格式 `pytorch_model.bin`，transformers 4.51.3 加载时会在**后台线程**偷偷去下一份 400MB 的 `model.safetensors`，脚本打印完了进程也要等几分钟才退出，像死机一样；本地目录已是 safetensors，加载零网络。HF 缓存 `C:\Users\meish\.cache\huggingface\hub` 里也有原始下载，作后备 |
| 1.6 节 `model=r"D:\gitcode\model\..."` | 改成 `model="./models/roberta-base-finetuned-dianping-chinese"` | 那是讲师本机路径，思路一样：本地目录 |
| 5.6 节 `evaluate.load('./evaluate-main/metrics/accuracy/accuracy.py')` | 路径原样可用，`evaluate-main/` 已 clone 到本目录（git 不跟踪） | GitHub 直连有时不稳，先拉好 |
| 4.6 节 `dtype="auto"` | 本环境 transformers 是 4.51.3，这个参数名要写 `torch_dtype="auto"` | 课件那段注释按 v5 写的，与 1.4 节钉的 4.51.3 版本不一致——课件自身的小矛盾 |
| `device=0` 用 GPU | 本机是 Intel 集显、无 NVIDIA 卡，`torch.cuda.is_available()` 恒为 False，全部走 CPU | 课件用的都是 400MB 级小模型，CPU 推理秒级，训练慢一些但能跑 |

## 已预下载的模型（HF 缓存）

- `hfl/chinese-macbert-base` —— 第 3/4 章的分词器与底座
- `uer/roberta-base-finetuned-dianping-chinese` —— 第 1/2 章的中文情感分类 pipeline

下载时排除了 `*.h5`（TensorFlow）和 `*.msgpack`（Flax）权重，只留 PyTorch 用的，省一半流量。
