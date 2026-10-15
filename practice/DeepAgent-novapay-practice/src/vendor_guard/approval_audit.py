"""人工审批审计记录。

报告正文可以由模型生成，但人工决定、操作时间、操作账户和工具执行状态必须
来自应用代码。本模块把这些可信字段渲染为 Markdown，并通过唯一标记实现幂等
追加，避免重试时重复写入同一条审批记录。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class ApprovalAuditRecord:
    """一条由可信 CLI 生成的人工审批记录。

    proposed_decision 是 Agent 的建议；human_decision 是审批人的真实选择；
    execution_status 描述恢复工作流后提交工具是否真正执行。三者不能混为一谈。
    """

    record_id: str
    vendor_name: str
    proposed_decision: str
    human_decision: str
    handled_at: datetime
    operator: str
    thread_id: str
    trace_url: str | None
    execution_status: str


def resolve_report_path(project_root: Path, virtual_path: str) -> Path:
    """将 Agent 使用的虚拟报告路径安全映射到项目内的 reports 目录。

    Agent 返回的是 POSIX 风格虚拟路径，例如 /reports/ACME/report.md。这里先
    统一分隔符，再 resolve 并执行目录包含检查，防止通过 ``..`` 或反斜杠把
    审批记录写入项目其他位置。
    """
    normalized = virtual_path.replace("\\", "/")
    relative = PurePosixPath(normalized.lstrip("/"))
    if not relative.parts or relative.parts[0] != "reports":
        raise ValueError("审批报告路径必须位于 /reports/ 目录")

    reports_root = (project_root / "reports").resolve()
    target = (project_root / Path(*relative.parts)).resolve()
    try:
        target.relative_to(reports_root)
    except ValueError as error:
        raise ValueError("审批报告路径越出了 /reports/ 目录") from error

    if target.suffix.lower() != ".md":
        raise ValueError("审批报告必须是 Markdown 文件")
    return target


def _markdown_cell(value: str) -> str:
    """转义 Markdown 表格单元格中的控制字符。"""
    return (
        value.replace("|", "\\|")
        .replace("\r\n", "<br>")
        .replace("\n", "<br>")
    )


def _render_record(record: ApprovalAuditRecord) -> str:
    """把结构化审批记录渲染成带幂等标记的 Markdown 表格。"""
    # 审批时间缺少时区会导致跨地区审计无法还原先后顺序，因此宁可拒绝写入，
    # 也不保存一个含义不完整的本地时间。
    if record.handled_at.tzinfo is None:
        raise ValueError("人工处理时间必须包含时区")
    if record.human_decision not in {"approve", "reject"}:
        raise ValueError("人工处理结果必须是 approve 或 reject")

    human_result = (
        "同意执行提交"
        if record.human_decision == "approve"
        else "拒绝执行提交"
    )
    trace = record.trace_url or "未启用或未获取到"
    handled_at = record.handled_at.isoformat(timespec="seconds")
    rows = [
        ("审批记录 ID", record.record_id),
        ("供应商", record.vendor_name),
        ("建议准入决定", record.proposed_decision),
        ("人工处理结果", human_result),
        ("人工处理时间", handled_at),
        ("操作人（本机账户，未经身份认证）", record.operator),
        ("工作流线程", record.thread_id),
        ("提交状态", record.execution_status),
        ("LangSmith Trace", trace),
    ]
    table = "\n".join(
        f"| {_markdown_cell(label)} | {_markdown_cell(value)} |"
        for label, value in rows
    )
    # HTML 注释不会影响报告阅读，但可作为机器可识别的唯一键。相比搜索表格
    # 文本，它不受中文措辞或 Markdown 格式调整影响。
    marker = f"<!-- vendor-guard-approval:{record.record_id} -->"
    return (
        f"{marker}\n"
        "## 人工审批记录\n\n"
        "| 字段 | 内容 |\n"
        "|---|---|\n"
        f"{table}\n"
    )


def _finalize_pending_notice(
    content: str,
    record: ApprovalAuditRecord,
) -> str:
    """把模型生成的“待审批”提示替换为可信的最终审批状态。

    只替换 Markdown 引用块中的候选提示，避免误改正文里对审批制度的说明。
    如果模型没有生成待审批提示，则保持正文不变，审批表仍会正常追加。
    """
    if record.human_decision == "approve":
        final_notice = "> ✅ **人工审批已完成：同意执行提交。**"
    else:
        final_notice = "> ❌ **人工审批已完成：拒绝执行提交，准入建议未提交。**"

    lines = content.splitlines(keepends=True)
    replaced = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        is_pending_notice = (
            stripped.startswith(">")
            and "审批" in stripped
            and any(
                phrase in stripped
                for phrase in ("待审批", "等待", "审批结果将", "待审批完成")
            )
        )
        if is_pending_notice:
            newline = "\r\n" if line.endswith("\r\n") else "\n"
            if not line.endswith(("\n", "\r")):
                newline = ""
            lines[index] = final_notice + newline
            replaced = True
    return "".join(lines) if replaced else content


def append_approval_audit(report_path: Path, record: ApprovalAuditRecord) -> bool:
    """把审批记录追加到报告；同一记录重复写入时保持幂等。

    返回 True 表示发生了写入，False 表示 record_id 已存在。调用方可据此决定
    是否打印“记录已写入”，而不需要再次读取报告。
    """
    if not report_path.is_file():
        raise FileNotFoundError(f"找不到待写入审批记录的报告：{report_path}")

    content = report_path.read_text(encoding="utf-8")
    marker = f"<!-- vendor-guard-approval:{record.record_id} -->"
    if marker in content:
        return False

    finalized_content = _finalize_pending_notice(content, record)
    if finalized_content != content:
        report_path.write_text(finalized_content, encoding="utf-8", newline="")
        content = finalized_content

    # 保证审批记录与正文之间只有一个空段落，同时固定使用 LF 写入新增内容，
    # 避免 Windows 默认换行影响跨平台 diff。
    separator = "\n" if content.endswith("\n") else "\n\n"
    with report_path.open("a", encoding="utf-8", newline="\n") as report:
        report.write(separator)
        report.write(_render_record(record))
    return True
