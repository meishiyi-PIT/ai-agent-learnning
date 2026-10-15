"""由应用代码维护的可信报告生命周期与语义约束。

模型负责撰写业务内容，应用代码负责不能靠语言模型猜测的部分：运行日期、历史
报告隔离，以及风险等级与证据状态的基本一致性。这里的校验是轻量确定性门禁，
不是完整的 Markdown 解析器或业务评审器。
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4


# 模型生成的标题层级和文案并不固定，可能带阿拉伯数字、中文序号或英文后缀：
# ``## 3. 安全审查（Security Review）``、
# ``### 2.1 安全域 — 风险等级：medium``、
# ``### 3.1 安全审查（Security Review）``。
# 这里允许二至四级标题，后续按照实际标题层级截取整个安全章节。
_SECURITY_SECTION_HEADING = re.compile(
    r"^(?P<marks>#{2,4})\s+"
    r"(?:(?:\d+(?:\.\d+)*|[一二三四五六七八九十]+)[.、)）]?\s*)?"
    r"安全(?:域|审查)",
    re.MULTILINE,
)
_MARKDOWN_SECTION_HEADING = re.compile(
    r"^(?P<marks>#{2,4})\s+",
    re.MULTILINE,
)


def archive_existing_report(
    project_root: Path,
    report_path: Path,
    archived_at: datetime,
) -> Path | None:
    """运行前归档旧报告，避免历史审批结果进入新一轮 Agent 上下文。

    旧报告会移动到 ``report-history/<供应商>/``，文件名包含带时区时间和随机
    后缀。移动而不是复制可以保证固定目标路径在 Agent 启动时确实不存在。
    历史目录同时由文件权限规则禁止 Agent 读取，但仍可供人工追溯。
    """
    if not report_path.is_file():
        return None
    if archived_at.tzinfo is None:
        raise ValueError("报告归档时间必须包含时区")

    project_root = project_root.resolve()
    reports_root = (project_root / "reports").resolve()
    resolved_report = report_path.resolve()
    try:
        relative_report = resolved_report.relative_to(reports_root)
    except ValueError as error:
        raise ValueError("只能归档项目 reports 目录内的报告") from error

    # Windows 文件名不能包含冒号，因此使用紧凑时间格式；随机后缀避免同一
    # 微秒内的并发或重试产生文件名冲突。
    timestamp = archived_at.strftime("%Y%m%dT%H%M%S.%f%z")
    archive_directory = (
        project_root / "report-history" / relative_report.parent
    )
    archive_directory.mkdir(parents=True, exist_ok=True)
    archive_path = archive_directory / (
        f"{resolved_report.stem}-{timestamp}-{uuid4().hex[:8]}"
        f"{resolved_report.suffix}"
    )
    resolved_report.replace(archive_path)
    return archive_path


def stamp_report_date(report_path: Path, report_date: date) -> bool:
    """用应用提供的日期替换报告日期，避免模型猜测系统时间。

    优先替换已有日期行；如果模型遗漏日期，则插入一级标题之后。返回值表示
    文件是否发生变化，使调用方和测试能够验证该操作的幂等性。
    """
    if not report_path.is_file():
        raise FileNotFoundError(f"找不到待写入日期的报告：{report_path}")

    content = report_path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    canonical_line = f"**报告日期：** {report_date.isoformat()}"

    # 同时兼容中文和英文冒号，但统一写回一种规范格式。
    for index, line in enumerate(lines):
        if line.strip().startswith(("**报告日期：", "**报告日期:")):
            newline = "\r\n" if line.endswith("\r\n") else "\n"
            if not line.endswith(("\n", "\r")):
                newline = ""
            replacement = canonical_line + newline
            if line == replacement:
                return False
            lines[index] = replacement
            report_path.write_text("".join(lines), encoding="utf-8", newline="")
            return True

    heading_index = next(
        (index for index, line in enumerate(lines) if line.lstrip().startswith("# ")),
        None,
    )
    if heading_index is None:
        raise ValueError("报告缺少一级标题，无法写入报告日期")

    lines.insert(heading_index + 1, f"\n{canonical_line}\n")
    report_path.write_text("".join(lines), encoding="utf-8", newline="")
    return True


def validate_report_risk_semantics(report_path: Path) -> None:
    """拒绝风险等级与证据状态混用或安全域汇总自相矛盾的报告。

    当前门禁检查两件事：

    1. 安全明细必须包含独立的“证据状态”列；
    2. 安全域总评为 low 时，明细中不能仍有 medium/high/critical。

    该函数故意不对报告做自动修复，因为应用代码无法安全推断模型遗漏的业务
    事实；发现矛盾时应中止审批，让生成协议或证据处理逻辑得到修正。
    """
    content = report_path.read_text(encoding="utf-8")
    security_heading = _SECURITY_SECTION_HEADING.search(content)
    if security_heading is None:
        raise ValueError("报告缺少安全域风险明细")

    # 安全章节内部可能继续使用更深一级的子标题。章节边界必须是“同级或更高”
    # 的下一个标题：例如安全章节为 ## 时，### 3.1/3.2 都属于其正文，直到
    # 下一个 ## 法务审查才结束。
    security_heading_level = len(security_heading.group("marks"))
    next_heading = next(
        (
            heading
            for heading in _MARKDOWN_SECTION_HEADING.finditer(
                content,
                security_heading.end(),
            )
            if len(heading.group("marks")) <= security_heading_level
        ),
        None,
    )
    security_section = (
        content[security_heading.start():]
        if next_heading is None
        else content[security_heading.start():next_heading.start()]
    )
    if "证据状态" not in security_section:
        raise ValueError("安全域风险表必须将风险等级与证据状态分列")

    # 汇总表的第一列存在中英文和“安全域/安全审查”多种写法。这里只寻找安全
    # 汇总行，第二列才是该专业域的总体风险等级。
    security_summary = next(
        (
            line
            for line in content.splitlines()
            if line.lstrip().startswith("|")
            and (
                "安全 (Security)" in line
                or "安全（Security）" in line
                or re.search(r"\|\s*\**安全(?:域|审查)?\**\s*\|", line)
            )
        ),
        "",
    )
    summary_cells = [
        cell.strip().strip("*").strip().lower()
        for cell in security_summary.strip().strip("|").split("|")
    ]
    overall_level = summary_cells[1] if len(summary_cells) > 1 else ""
    # 聚合冲突只需要在总评为 low 时继续扫描。总评本身已是 medium 以上或
    # unknown 时，即使明细存在高风险，也不存在“被错误降级为 low”的问题。
    if overall_level not in {"low", "低"}:
        return

    blocking_levels = {"medium", "high", "critical", "中", "高", "严重"}
    detailed_levels: set[str] = set()
    for line in security_section.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [
            cell.strip().strip("*").strip().lower()
            for cell in line.strip().strip("|").split("|")
        ]
        if len(cells) > 1:
            detailed_levels.add(cells[1])

    conflicts = sorted(detailed_levels & blocking_levels)
    if conflicts:
        raise ValueError(
            "安全域总评为 low，但存在未整改的更高风险项："
            + ", ".join(conflicts)
        )
