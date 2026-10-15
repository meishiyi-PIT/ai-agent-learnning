"""本地 Fixture 数据访问层。

该模块不依赖 LangChain 或 Deep Agents，可独立进行单元测试。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonRepository:
    """读取项目中的固定 JSON 数据。

    Repository 隔离了工具层与文件格式：Agent 工具只关心业务查询，不需要知道
    JSON 文件名和目录布局。当前实现每次查询重新读取文件，适合体积很小的课程
    Fixture，也确保修改 Fixture 后无需重启进程即可生效。
    """

    # 【Python 基础】__init__ 才是“真构造函数”（对应 Java 构造器），造实例时
    # 自动执行：JsonRepository(某目录) → 触发 __init__。self = Java 的 this，
    # 但 Python 必须把它显式写成第一个参数。“self.fixtures_dir = ...”即给
    # 实例挂字段——Python 不用先声明字段，赋值即创建。
    def __init__(self, fixtures_dir: Path) -> None:
        self.fixtures_dir = fixtures_dir.resolve()

    # 【Python 基础】方法名前的单下划线 “_” = 约定俗成的 private（Java 的
    # private 是编译器强制，Python 没有强制私有，只靠命名告诉使用者：
    # “内部实现，外面别调”。）
    def _read(self, filename: str) -> dict[str, Any]:
        """读取一个受 fixtures_dir 约束的 JSON 对象。"""
        path = (self.fixtures_dir / filename).resolve()
        # resolve() 会消解 ../；再检查父目录可阻止调用者借文件名逃出 fixtures。
        if self.fixtures_dir not in path.parents:
            raise ValueError("Fixture 路径越界")
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def get_vendor(self, vendor_name: str) -> dict[str, Any]:
        """按不区分大小写的供应商名查询主数据。"""
        vendors = self._read("vendor_registry.json")["vendors"]
        # 未命中时返回结构化结果而不是抛 KeyError，让 Agent 能明确区分
        # “数据源可用但供应商不存在”和“工具执行失败”。
        return vendors.get(vendor_name.upper(), {"vendor": vendor_name, "found": False})

    def get_sanctions(self, vendor_name: str) -> list[dict[str, Any]]:
        """返回该供应商的全部制裁名单记录。"""
        records = self._read("sanctions.json")["records"]
        key = vendor_name.upper()
        # 【Python 基础】列表推导式（带过滤）：[表达式 for 元素 in 列表 if 条件]
        # 读法顺序：遍历 records → 只留 vendor 名匹配的 → 收集成新列表。
        # 等价 Java：records.stream().filter(r -> ...).collect(toList())。
        # 记忆窍门：把 for/if 想成“横着写的循环”，最前面的表达式是每轮往新列表塞的值。
        return [record for record in records if record["vendor"].upper() == key]

    def get_incidents(self, vendor_name: str) -> list[dict[str, Any]]:
        """返回该供应商的全部安全事故记录。"""
        records = self._read("security_incidents.json")["records"]
        key = vendor_name.upper()
        return [record for record in records if record["vendor"].upper() == key]

    def get_adverse_news(self, vendor_name: str) -> list[dict[str, Any]]:
        """返回该供应商的全部负面新闻记录。"""
        records = self._read("adverse_news.json")["records"]
        key = vendor_name.upper()
        return [record for record in records if record["vendor"].upper() == key]
