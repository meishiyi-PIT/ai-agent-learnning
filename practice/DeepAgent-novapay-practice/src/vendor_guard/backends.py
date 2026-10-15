"""Deep Agents 虚拟文件系统与文件权限配置。

Agent 始终操作 ``/data-room/...`` 这样的虚拟 POSIX 路径。本模块决定这些路径
最终落到本地磁盘、当前线程状态还是长期 Store，并额外限制哪些区域只读。
"""

from __future__ import annotations

from pathlib import Path

from deepagents import FilesystemPermission
from deepagents.backends import (
    CompositeBackend,
    FilesystemBackend,
    StateBackend,
    StoreBackend,
)


def build_backend(project_root: Path, namespace: tuple[str, ...]) -> CompositeBackend:
    """按数据生命周期划分真实文件、线程文件和长期记忆。

    - 默认 FilesystemBackend：输入材料、政策、Skill 和最终报告；
    - /workspace/：仅属于本次图状态的专家中间产物；
    - /memories/：按组织与助手隔离的跨线程知识。
    """
    return CompositeBackend(
        # 未命中特殊路由的虚拟路径映射到项目根目录，例如 /data-room/ 和
        # /reports/；virtual_mode 让 Agent 始终使用统一的 POSIX 风格路径。
        default=FilesystemBackend(
            root_dir=str(project_root.resolve()),
            virtual_mode=True,
        ),
        routes={
            # StateBackend 的内容跟随 LangGraph 状态，可参与暂停和恢复；它不是
            # project_root 下的真实目录，因此不会污染下一次独立评估沙箱。
            # 长期经验才进入带命名空间的 Store。
            "/workspace/": StateBackend(),
            # lambda 是“匿名函数”（相当于 Java 的 lambda）：lambda 参数: 返回值。
            # 这里 StoreBackend 要的是“一个能算出命名空间的函数”，而不是命名空间本身，
            # 所以传一个函数进去，框架运行时会带 runtime 回调它。参数名写成 _runtime
            # （下划线开头）是约定：表示“这个参数我收下但用不到”，忽略它，直接返回外层的
            # namespace 元组。等价于先 def f(_runtime): return namespace 再传 f，只是懒得起名。
            "/memories/": StoreBackend(namespace=lambda _runtime: namespace),
        },
    )


def build_permissions() -> list[FilesystemPermission]:
    """保护原始资料、组织政策、Skill 和历史审批报告。

    权限规则在文件工具执行层生效，比仅在 Prompt 中要求“不要修改”更可靠。
    未命中 deny 的路径仍按 Backend 能力正常读写，因此 Agent 可以生成报告。
    """
    return [
        # 只禁止写入，Agent 仍可读取这些目录作为调查证据和执行规则。
        FilesystemPermission(
            operations=["write"],
            paths=["/data-room/**", "/policies/**", "/skills/**"],
            mode="deny",
        ),
        # 历史报告由 CLI 保存，只用于人工追溯。禁止 Agent 读取旧审批结果，
        # 避免新一轮调查继承上一次的批准或拒绝状态。
        FilesystemPermission(
            operations=["read", "write"],
            paths=["/report-history/**"],
            mode="deny",
        ),
    ]
