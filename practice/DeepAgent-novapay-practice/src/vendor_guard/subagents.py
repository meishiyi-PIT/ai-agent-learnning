"""四个专业 Subagent（子智能体）的声明式配置。

每个字典会由 Deep Agents 转换成独立专业角色。不同角色使用独立 Prompt、
Skill 和最小工具集合，但共享主管提供的文件后端，从而可以把详细发现写到
``/workspace/findings/`` 后再由主管汇总。
"""

from __future__ import annotations

from vendor_guard.tools import (
    lookup_security_incidents,
    query_vendor_registry,
    search_adverse_news,
    search_sanctions,
)


def build_subagents() -> list[dict]:
    """创建四个最小权限的同步专业子 Agent。

    返回新列表而不是模块级可变单例，避免测试或框架内部对配置做原地修改后
    污染下一次 build_vendor_guard()。
    """
    # 每个专家只获得本领域查询工具；完整证据写入共享 /workspace/findings/，
    # 返回给主管的内容则刻意压缩，避免多个领域的上下文同时挤占模型窗口。
    # description 用于主管选择委派对象；system_prompt 约束专家内部执行；
    # tools 决定硬权限边界；skills 提供该领域更详细、可维护的工作方法。
    return [
        {
            "name": "security-auditor",
            "description": "审查安全问卷、渗透报告、数据保护和安全事故。",
            "system_prompt": """
读取 /data-room/{供应商}/ 中的安全资料。
使用 security-review Skill 评分；无证据必须标记 unknown。
严格区分风险严重度和证据状态：问卷是自述证据，缺少独立佐证时标为
“自述待验证”并降低置信度，不得自动改成 unknown。只有资料完全未涉及、
无法判断时才使用 unknown。存在未整改 medium 或关键 unknown 时总评不得为 low。
完整发现写入 /workspace/findings/security.md。
只返回风险等级、三条关键证据和待补材料，最多 300 字。
""",
            "tools": [lookup_security_incidents],
            "skills": ["/skills/security-review/"],
        },
        {
            "name": "legal-auditor",
            "description": "审查合同、制裁、数据处理条款和合规红线。",
            "system_prompt": """
读取合同和 /policies/vendor-onboarding.md，检查红线与制裁命中。
完整发现写入 /workspace/findings/legal.md。
只返回红线、证据位置和建议修改，最多 300 字。
""",
            "tools": [search_sanctions],
            "skills": ["/skills/legal-review/"],
        },
        {
            "name": "finance-analyst",
            "description": "分析财务健康、履约记录和供应中断风险。",
            "system_prompt": """
分析财务文件和供应商主数据，禁止虚构缺失指标。
完整发现写入 /workspace/findings/finance.md。
只返回关键指标、异常项和置信度，最多 300 字。
""",
            "tools": [query_vendor_registry],
            "skills": ["/skills/finance-review/"],
        },
        {
            "name": "reputation-researcher",
            "description": "调查诉讼、负面新闻和声誉风险。",
            "system_prompt": """
检索近两年负面信息，区分事实、指控和重复转载。
完整发现写入 /workspace/findings/reputation.md。
只返回已核实事件、来源和置信度，最多 300 字。
""",
            "tools": [search_adverse_news],
            "skills": ["/skills/reputation-review/"],
        },
    ]
