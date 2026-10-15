# repos/ —— 课程代码仓库打包

公司网络不一定能访问课程 GitLab（`git.miaoatech.cn`），所以把四个仓库用 `git bundle` 整个带走（全部分支 + 标签），`scripts/setup-company.bat` 会自动还原。手动还原方法：

```bat
cd C:\workspace
git clone ai-agent-learnning\repos\zhifu-platform.bundle zhifu-platform
cd zhifu-platform
git checkout course/09-course-delivery
git remote set-url origin https://git.miaoatech.cn/liugang/zhifu-platform.git
```

| bundle | 原始地址 | 学习用分支 | 说明 |
|---|---|---|---|
| `zhifu-platform.bundle` | https://git.miaoatech.cn/liugang/zhifu-platform.git | `course/09-course-delivery` | 当前主线。10 个 `course/0x-*` 分支 + `course-0x-*` 标签，看 diff 用 tag |
| `harness_zbt.bundle` | https://git.miaoatech.cn/yangxiaolong/harness_zbt.git | `phaseThree` | 模块四智保通，phaseOne/Two/Three |
| `DeepAgent.bundle` | https://git.miaoatech.cn/yangxiaolong/DeepAgent.git | `master` | DeepAgents VendorGuard 课程仓库 |
| `meishiyi.bundle` | https://git.miaoatech.cn/meishiyi/meishiyi.git | `master` | 我自己的作业仓库 |

## local-changes/

工作区里这些仓库 **尚未 commit** 的改动快照（打包时刻见各目录 `HEAD.txt`）：

- `tracked.patch`：对已跟踪文件的修改，`git -C C:\workspace\<仓库> apply --3way <patch>` 打上
- `untracked/`：新增的文件，原样拷回仓库目录即可

| 仓库 | 里面是什么 |
|---|---|
| `harness_zbt` | 续保规划作业：`domains/renewal/`、`api/v1/renewal_advice.py`、`skills/renewal-planning/SKILL.md`、知识种子 md，以及 tools/registries/schemas 的挂接改动 |
| `DeepAgent` | 随堂改动 + `examples/llm_invoke_demo.py` |
| `meishiyi` | `09_HuggingFace/` 整套练习脚本（arch_train / inference_deploy / dist / lora 系列）；不含 `.venv` 和模型 |
| `zhifu-platform` | 无（只读） |

刷新方式（在改动所在的机器上）：`powershell -ExecutionPolicy Bypass -File scripts\sync-push.ps1 -WithRepos`。

没带的：`code/`（老师的模块五六代码，1.9 GB 含数据集）→ `git clone https://git.miaoatech.cn/ryanxiao/code.git`。
