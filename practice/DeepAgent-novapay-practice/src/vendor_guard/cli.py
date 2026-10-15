"""VendorGuard 命令行入口。

CLI 是模型世界与可信应用世界之间的边界，主要负责：

1. 准备运行标识、归档历史报告并启动 Agent；
2. 校正报告日期、执行确定性语义校验；
3. 接收人工 approve/reject，使用同一 thread_id 恢复工作流；
4. 把真实审批结果写入报告，并输出不依赖模型解释的最终状态。
"""

from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime
from typing import Literal
from uuid import uuid4

from langgraph.types import Command

from vendor_guard.agent import build_vendor_guard
from vendor_guard.approval_audit import (
    ApprovalAuditRecord,
    append_approval_audit,
    resolve_report_path,
)
from vendor_guard.observability import (
    build_run_config,
    get_latest_trace_url,
    langsmith_status,
    langsmith_trace_scope,
)
from vendor_guard.report_metadata import (
    archive_existing_report,
    stamp_report_date,
    validate_report_risk_semantics,
)
from vendor_guard.settings import Settings


def _should_reexec_utf8(platform_name: str, utf8_mode: int) -> bool:
    """判断是否需要在 Windows 上以 UTF-8 模式重新启动。"""
    return platform_name == "nt" and utf8_mode == 0


def _build_utf8_reexec_command(arguments: list[str]) -> list[str]:
    """生成启用 UTF-8 模式的等价 CLI 启动命令。"""
    return [
        sys.executable,
        "-X",
        "utf8",
        "-m",
        "vendor_guard.cli",
        *arguments,
    ]


def _run_utf8_child(
    arguments: list[str],
    environment: dict[str, str],
    *,
    runner: Callable[..., subprocess.CompletedProcess] | None = None,
) -> int:
    """运行 UTF-8 子进程，并把父进程收到的 Ctrl+C 转成标准退出码。

    Windows 终端会把 Ctrl+C 同时广播给等待中的父进程和实际执行 Agent 的
    子进程。子进程可以优雅处理审批取消，但父进程的 subprocess.run() 仍可能
    收到 KeyboardInterrupt；这里统一转换为 130，避免父层再次打印 Traceback。
    """
    runner = runner or subprocess.run
    try:
        completed = runner(
            _build_utf8_reexec_command(arguments),
            env=environment,
            check=False,
        )
    except KeyboardInterrupt:
        return 130
    return completed.returncode


def _ensure_utf8_mode() -> None:
    """
    避免 Windows 将 Deep Agents 子进程的 UTF-8 输出按 GBK 解码。

    PYTHONUTF8 必须在 Python 解释器启动前生效，因此不能等到
    Settings 读取 .env 后再设置。这里仅在必要时启动一次等价子进程。
    """
    if not _should_reexec_utf8(os.name, sys.flags.utf8_mode):
        return

    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    exit_code = _run_utf8_child(
        sys.argv[1:],
        environment,
    )
    raise SystemExit(exit_code)


def _print_final_answer(result) -> None:
    """从 Deep Agent 的状态对象中提取最后一条可展示消息。"""
    # version="v2" 的 invoke 结果通常通过 value 暴露图状态；保留对普通 dict
    # 返回值的兼容，便于测试或未来替换调用方式。
    values = getattr(result, "value", result)
    messages = values.get("messages", []) if isinstance(values, dict) else []
    if messages:
        print(messages[-1].content)


def _approval_outcome_message(
    *,
    vendor_name: str,
    proposed_decision: str,
    approved: bool,
    report_path,
) -> str:
    """生成可信的最终审批状态，不采用模型对审批结果的二次解释。

    人工是否批准是 CLI 直接获得的输入，属于应用事实。即使恢复后的模型消息
    出现“仍待审批”等口径漂移，终端也只展示这里生成的确定性结果。
    """
    if approved:
        outcome = "已批准执行，提交工具已执行"
    else:
        outcome = "未批准执行，准入建议未提交"
    return (
        f"人工审批已完成：{outcome}。\n"
        f"供应商：{vendor_name}；准入建议：{proposed_decision}。\n"
        f"报告：{report_path}"
    )


def _read_approval_decision(
    input_func: Callable[[str], str] | None = None,
) -> Literal["approve", "reject", "cancel"]:
    """读取人工审批输入，并把终端中断与业务拒绝明确分开。

    只有显式输入 y 才表示 approve；普通的 n 或空输入表示 reject。Ctrl+C 和
    stdin 关闭说明用户没有完成审批，返回 cancel，调用方不得把它记录成拒绝。
    input_func 参数用于单元测试注入，不需要启动真实交互终端。
    """
    input_func = input_func or input
    try:
        raw_decision = input_func("批准执行？[y/N] ")
    except (KeyboardInterrupt, EOFError):
        return "cancel"
    return "approve" if raw_decision.strip().lower() == "y" else "reject"


def _print_trace_url(settings: Settings, thread_id: str, *, client=None) -> str | None:
    """查询并打印本次 Trace 链接；失败时不影响业务流程。"""
    try:
        trace_url = get_latest_trace_url(
            settings,
            thread_id,
            client=client,
        )
    except Exception as error:
        print(
            "\nLangSmith Trace 链接获取失败："
            f"{type(error).__name__}。请在控制台中打开项目 "
            f"{settings.langsmith_project}。"
        )
        return None

    if trace_url:
        print(f"\nLangSmith Trace：{trace_url}")
        return trace_url

    print(
        "\nLangSmith Trace 已提交，但暂未查询到链接。"
        f"请稍后刷新项目 {settings.langsmith_project}。"
    )
    return None


def main() -> None:
    """执行一次完整的交互式供应商准入流程。"""
    _ensure_utf8_mode()

    parser = argparse.ArgumentParser(description="运行 VendorGuard 供应商尽调")
    parser.add_argument("vendor", help="供应商名称，例如 ACME")
    # parse_args() 默认读取 sys.argv[1:]；这里的 vendor 是不带 -- 的位置参数。
    args = parser.parse_args()

    vendor = args.vendor.upper()
    settings = Settings.from_env()
    # thread_id 同时是 LangGraph Checkpointer 的状态键，也是 LangSmith Trace
    # 的检索元数据。首次 invoke 和审批恢复必须复用同一个值。
    thread_id = f"vendor-{vendor.lower()}-001"
    run_started_at = datetime.now().astimezone()
    report_date = run_started_at.date()
    generated_report_path = (
        settings.project_root / "reports" / vendor / "onboarding-report.md"
    )
    # 固定报告路径便于业务方查找，但会让新一轮 Agent 看见上一轮审批结果。
    # 因此每次运行先把旧报告移入受保护历史区，再从空白目标路径生成新报告。
    archived_report_path = archive_existing_report(
        settings.project_root,
        generated_report_path,
        run_started_at,
    )
    if archived_report_path is not None:
        print(f"历史报告已归档：{archived_report_path}")

    # 归档完成后再构建并调用 Agent，确保任何文件工具都看不到旧目标报告。
    agent = build_vendor_guard(settings)
    config = build_run_config(settings, vendor, thread_id)
    print(langsmith_status(settings))

    trace_url = None
    approval_outcome = None
    # tracing_context 包裹首次执行和审批恢复，使二者归入同一次业务 Trace。
    # Trace 关闭时该上下文仍可使用，只会返回 trace_client=None。
    with langsmith_trace_scope(settings) as trace_client:
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"评估供应商 {vendor} 是否可准入。"
                            f"读取 /data-room/{vendor}/，生成风险报告；"
                            f"本次报告日期必须使用 {report_date.isoformat()}；"
                            "必须从当前证据重新生成报告，不得复用历史报告或审批结果；"
                            "若建议准入或有条件准入，则提交人工审批。"
                        ),
                    }
                ]
            },
            config=config,
            version="v2",
        )

        # 以下检查发生在询问人工审批之前。报告不存在、日期不可信或风险语义
        # 自相矛盾时直接失败，避免审批人基于一份结构不合格的报告做决定。
        #
        # 报告日期属于可信运行元数据。即使模型忽略日期指令，也由应用代码
        # 统一校正，不能采用模型自行推测的日期。
        if not generated_report_path.is_file():
            raise RuntimeError("本次运行未生成新的供应商报告，已拒绝复用旧报告")
        stamp_report_date(generated_report_path, report_date)
        validate_report_risk_semantics(generated_report_path)

        # submit_onboarding_decision 命中 interrupt_on 后，第一次 invoke 会停在
        # 工具执行前，并把待审批动作放进 interrupts，而不是直接产生副作用。
        if result.interrupts:
            # Deep Agents 的 HITL 中断可能包含多个 action request。当前业务一次
            # 只允许提交一个准入决定，所以取第一个请求作为审批对象。
            request = result.interrupts[0].value["action_requests"][0]
            print("\n待人工审批：", request)
            if trace_client is not None:
                # Trace 默认可能仍在上传队列中；先 flush 才能立即查到本次运行。
                trace_client.flush()
                trace_url = _print_trace_url(
                    settings,
                    thread_id,
                    client=trace_client,
                )
                if trace_url:
                    print("请先打开以上链接检查执行过程，再决定是否批准。")
            decision = _read_approval_decision()
            if decision == "cancel":
                # cancel 不是业务拒绝：没有恢复工作流，也不写审批审计记录。
                # 使用 130（128 + SIGINT）让脚本或 CI 能识别本次运行由用户取消。
                print(
                    "\n已取消本次人工审批：未作出批准或拒绝决定，"
                    "提交工具未执行。报告已保留，重新运行时会自动归档。"
                )
                raise SystemExit(130)

            # 用户只需显式输入 y 才会 approve；空输入、n 和其他内容均按 reject
            # 处理，符合有副作用操作的 fail-closed 原则。
            approved = decision == "approve"
            handled_at = datetime.now().astimezone()
            request_args = request["args"]
            report_path = resolve_report_path(
                settings.project_root,
                request_args["report_path"],
            )
            record_id = str(uuid4())
            # 使用同一个 thread_id 恢复 Checkpointer 中的暂停状态，从中断点继续，
            # 而不是重新运行整次供应商调查。
            try:
                result = agent.invoke(
                    Command(resume={"decisions": [{"type": decision}]}),
                    config=config,
                    version="v2",
                )
            except Exception as error:
                # 即使恢复执行失败，也要留下“谁在何时做了什么决定”的记录。
                # execution_status 会区分审批决定本身与后续工具执行是否成功。
                execution_status = f"工作流恢复失败（{type(error).__name__}）"
                append_approval_audit(
                    report_path,
                    ApprovalAuditRecord(
                        record_id=record_id,
                        vendor_name=request_args["vendor_name"],
                        proposed_decision=request_args["decision"],
                        human_decision=decision,
                        handled_at=handled_at,
                        operator=getpass.getuser(),
                        thread_id=thread_id,
                        trace_url=trace_url,
                        execution_status=execution_status,
                    ),
                )
                raise

            # approve 时提交工具已经在恢复过程中执行；reject 时图会跳过工具。
            execution_status = (
                "提交工具已执行" if approved else "未执行（人工拒绝）"
            )
            audit_written = append_approval_audit(
                report_path,
                ApprovalAuditRecord(
                    record_id=record_id,
                    vendor_name=request_args["vendor_name"],
                    proposed_decision=request_args["decision"],
                    human_decision=decision,
                    handled_at=handled_at,
                    operator=getpass.getuser(),
                    thread_id=thread_id,
                    trace_url=trace_url,
                    execution_status=execution_status,
                ),
            )
            if audit_written:
                print(f"\n人工审批记录已写入：{report_path}")
            approval_outcome = _approval_outcome_message(
                vendor_name=request_args["vendor_name"],
                proposed_decision=request_args["decision"],
                approved=approved,
                report_path=report_path,
            )

        if approval_outcome is None:
            _print_final_answer(result)
        else:
            # 审批动作是可信边界；避免模型把“已审批但拒绝执行”重新描述为
            # “仍待审批”或“请再次提交审批”。
            print(approval_outcome)

    # 没有触发人工审批时，上方不会提前 flush/打印链接；在任务结束后补查一次。
    if settings.langsmith_tracing and trace_url is None:
        _print_trace_url(settings, thread_id)


if __name__ == "__main__":
    main()
