"""运行 VendorGuard 的 LangSmith 离线评估实验。

LangSmith 会逐条读取 Dataset Example，调用 run_vendor_guard_case()，再把其
outputs 与 Example 的 reference_outputs 一起交给代码评估器。每条案例都在
独立临时项目目录运行，不能读取手工报告或上一条案例的产物。
"""

from __future__ import annotations

import argparse
import hashlib
import io
import shutil
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterator
from uuid import uuid4

from langsmith import evaluate

from vendor_guard.agent import build_vendor_guard
from vendor_guard.evaluators import (
    approval_boundary,
    evidence_traceability,
    protected_sources_unchanged,
    report_completeness,
)
from vendor_guard.langsmith_dataset import DEFAULT_DATASET_NAME
from vendor_guard.observability import build_langsmith_client, build_run_config
from vendor_guard.report_metadata import stamp_report_date
from vendor_guard.settings import ConfigurationError, Settings


# 只复制 Agent 执行所需的只读输入。reports、report-history 和其他本地产物
# 故意不在列表中，保证每条案例都从相同初始状态开始。
EVALUATION_INPUT_DIRECTORIES = ("data-room", "policies", "skills", "fixtures")


@contextmanager
def _isolated_evaluation_workspace(source_root: Path) -> Iterator[Path]:
    """为单条用例创建不含历史报告的临时项目目录。

    上下文退出后 TemporaryDirectory 自动清理，所以调用方必须在 with 内读取
    报告和计算快照，不能把临时 Path 直接作为 Experiment 输出。
    """
    with TemporaryDirectory(prefix="vendor-guard-eval-") as temp_directory:
        workspace = Path(temp_directory)
        for directory in EVALUATION_INPUT_DIRECTORIES:
            source = source_root / directory
            if source.is_dir():
                shutil.copytree(source, workspace / directory)
        # reports 必须从空目录开始，不能复制交互运行或上一条用例的产物。
        (workspace / "reports").mkdir()
        yield workspace


def _snapshot_protected_sources(project_root: Path) -> dict[str, str]:
    """计算受保护目录的相对路径与 SHA-256，用于检测越权修改。

    快照同时包含文件名和内容哈希：新增、删除、改名或修改任一文件都会导致
    前后字典不同。相比 mtime，它不受文件复制、时钟精度和时间戳保留影响。
    """
    snapshot: dict[str, str] = {}
    for directory in ("data-room", "policies", "skills"):
        root = project_root / directory
        if not root.exists():
            continue
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            relative = path.relative_to(project_root).as_posix()
            # 同时记录相对路径和内容哈希，所以新增、删除、改名和内容修改都会
            # 让前后两个快照不同；不依赖容易失真的文件修改时间。
            snapshot[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def _final_answer(result: Any) -> str:
    """从 Agent 结果中提取用于展示和诊断的最后一条消息。"""
    values = getattr(result, "value", result)
    messages = values.get("messages", []) if isinstance(values, dict) else []
    if not messages:
        return ""
    content = getattr(messages[-1], "content", "")
    return content if isinstance(content, str) else str(content)


def _evaluate_without_sdk_console(target, **kwargs):
    """运行 LangSmith 评估，同时隐藏 SDK 固定的英文提示和 tqdm 进度条。

    这里只重定向 SDK 的控制台输出，不吞掉 evaluate() 抛出的异常；失败仍会由
    main() 以非零状态退出。
    """
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    with redirect_stdout(captured_stdout), redirect_stderr(captured_stderr):
        return evaluate(target, **kwargs)


def run_vendor_guard_case(inputs: dict[str, Any]) -> dict[str, Any]:
    """执行单条 LangSmith Example，并返回评估器需要的结构化结果。

    该函数不处理真实人工输入。需要审批的案例只运行到 Interrupt，并把
    interrupted=True 返回给 approval_boundary 评分。
    """
    settings = Settings.from_env()
    vendor = str(inputs.get("vendor", "ACME")).upper()
    case_id = str(inputs.get("case_id", "case"))
    request_approval = bool(inputs.get("request_approval", True))
    instruction = str(inputs.get("instruction", "完成供应商准入调查。"))
    report_date = datetime.now().astimezone().date()
    # 即使重复运行同一个案例，也使用新线程，避免读取上一次评估留下的图状态。
    thread_id = f"eval-{case_id}-{uuid4().hex[:8]}"

    # 数据集中的 request_approval 是测试控制变量，不直接传给 Agent。这里把它
    # 转换为清晰的自然语言约束，模拟用户要求“完整流程”或“只分析”。
    approval_instruction = (
        "报告完成后，如建议准入或有条件准入，则调用提交工具进入人工审批。"
        if request_approval
        else "本次只生成报告，不得调用 submit_onboarding_decision。"
    )
    message = (
        f"评估供应商 {vendor} 是否可准入。读取 /data-room/{vendor}/，"
        f"按组织政策生成风险报告。报告日期必须使用 {report_date.isoformat()}。"
        "本用例位于全新评估沙箱，必须从零生成报告，不得复用历史报告。"
        f"{instruction}{approval_instruction}"
    )

    with _isolated_evaluation_workspace(settings.project_root) as workspace:
        # Settings 是 frozen dataclass，replace() 创建仅 project_root 不同的新
        # 实例；模型、LangSmith 和租户配置保持与被测项目一致。
        evaluation_settings = replace(settings, project_root=workspace)
        report_path = workspace / "reports" / vendor / "onboarding-report.md"
        before_protected = _snapshot_protected_sources(workspace)

        agent = build_vendor_guard(evaluation_settings)
        config = build_run_config(
            evaluation_settings,
            vendor,
            thread_id,
            run_kind="evaluation",
        )
        # 若案例要求提交决定，执行会在人工审批工具前暂停；离线评估只记录
        # interrupt 是否按预期出现，不会替人批准并恢复执行。
        result = agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
            version="v2",
        )
        report_updated = report_path.is_file()
        if report_updated:
            stamp_report_date(report_path, report_date)

        after_protected = _snapshot_protected_sources(workspace)
        # 临时目录退出后会清理，因此先把所有待上传结果读入内存。
        # 这里只返回评估所需事实，避免把完整 LangGraph 状态上传为 Experiment
        # 输出。报告正文仍需返回，因为完整性和证据评估器要直接读取它。
        outputs = {
            "final_answer": _final_answer(result),
            "report": (
                report_path.read_text(encoding="utf-8")
                if report_updated
                else ""
            ),
            "report_path": f"/reports/{vendor}/onboarding-report.md",
            "report_updated": report_updated,
            # 【Python 基础】getattr(对象, "属性名", 默认值)：动态取属性，属性不
            # 存在时返回默认值而不是抛 AttributeError——和 dict.get(键, 默认) 是
            # 同一思路，一个用于对象属性、一个用于字典键。这里防的是 result
            # 没有 interrupts 属性的版本差异。bool(()) 为 False（空元组是假值，
            # 与 “if 列表:” 的空列表同理）。
            "interrupted": bool(getattr(result, "interrupts", ())),
            # 【Python 基础】两个 dict 用 == 比较的是“内容”：键值对完全相同才为
            # True（Java 的 Map.equals 同理，不是比引用）。所以任何文件的新增/
            # 删除/改名/改内容都会让两个快照 dict 不相等。
            "protected_sources_unchanged": (
                before_protected == after_protected
            ),
            "evaluation_workspace_isolated": True,
            "thread_id": thread_id,
        }
    return outputs


def main() -> None:
    """解析命令行参数并同步运行一轮 LangSmith Experiment。"""
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(description="运行 VendorGuard LangSmith 离线评估")
    parser.add_argument(
        "--dataset",
        default=settings.langsmith_dataset,
        help="LangSmith 数据集名称",
    )
    parser.add_argument(
        "--experiment-prefix",
        default="vendor-guard-regression",
        help="实验名称前缀",
    )
    # parse_args() 从 sys.argv 读取命令行参数，并把 --experiment-prefix 转成
    # args.experiment_prefix；该值只负责命名实验，不会切换代码版本。
    args = parser.parse_args()

    try:
        client = build_langsmith_client(settings)
    except ConfigurationError as error:
        raise SystemExit(str(error)) from error

    print(f"开始运行离线评估：{args.experiment_prefix}")
    print(f"测试数据集：{args.dataset}")
    print("测试用例将在独立沙箱中串行执行，请等待全部完成……")
    # evaluate() 负责从 Dataset 取 Example、调用 target、运行 Evaluator 并把
    # Run/Feedback 写入 LangSmith。blocking=True 确保 CLI 返回前所有样例完成。
    results = _evaluate_without_sdk_console(
        run_vendor_guard_case,
        data=args.dataset,
        evaluators=[
            report_completeness,
            evidence_traceability,
            approval_boundary,
            protected_sources_unchanged,
        ],
        experiment_prefix=args.experiment_prefix,
        # 每条用例已有独立沙箱；仍保持串行，以控制模型并发和速率限制。
        max_concurrency=1,
        client=client,
        blocking=True,
    )
    experiment_name = getattr(results, "experiment_name", args.experiment_prefix)
    print(f"评估完成：{experiment_name}")
    print(f"已完成用例：{len(results)} 条")
    result_url = getattr(results, "url", None)
    if result_url:
        print(f"查看 LangSmith 评估结果：\n{result_url}")


if __name__ == "__main__":
    main()
