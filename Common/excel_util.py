"""
Common/excel_util.py — Excel 读写封装

核心功能：读取 Excel 指定 sheet 数据，返回列表格式供 pytest 做数据驱动。
设计要点：
  - 使用 openpyxl 读取 .xlsx 文件
  - 表头行自动映射为字段名
  - 支持动态列，Excel 增减列不影响代码
  - 仅返回 enabled=Y 的用例
  - 支持 login_status 列控制鉴权
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import openpyxl

from Common.path_util import get_excel_path
from Common.log_util import info, warning, error


# ---------------------------------------------------------------------------
# 数据模型：单条测试用例
# ---------------------------------------------------------------------------

@dataclass
class ApiCaseData:
    """
    Excel 用例数据模型。

    对应 Excel 模板的列定义，提供类型安全的访问接口。
    """
    case_id: str = ""
    interface_name: str = ""
    url: str = ""
    method: str = "GET"
    headers: str = ""              # JSON 字符串
    params: str = ""               # JSON 字符串（查询参数或请求体）
    expected_result: str = ""      # JSON 字符串（预期断言）
    replace_flag: str = ""         # 替换变量标识：Y/N
    extract_expression: str = ""   # jsonpath 提取表达式
    global_var_name: str = ""      # 存入全局变量的变量名
    db_check_sql: str = ""         # 数据库校验 SQL
    db_expected_value: str = ""    # 数据库预期值
    login_status: str = "Y"        # 是否鉴权：Y=自动注入Token, N=不注入
    enabled: str = "Y"
    module: str = ""               # 所属模块
    remark: str = ""

    def parse_headers(self) -> dict[str, Any]:
        """解析请求头 JSON。"""
        return _safe_json_parse(self.headers, {})

    def parse_params(self) -> dict[str, Any] | None:
        """解析请求参数 JSON。"""
        if not self.params or not self.params.strip():
            return None
        return _safe_json_parse(self.params, {})

    def parse_expected_result(self) -> dict[str, Any]:
        """解析预期结果 JSON。"""
        return _safe_json_parse(self.expected_result, {})

    @property
    def is_enabled(self) -> bool:
        return self.enabled.strip().upper() == "Y"

    @property
    def need_replace(self) -> bool:
        return self.replace_flag.strip().upper() == "Y"

    @property
    def need_auth(self) -> bool:
        """是否需要鉴权注入Token。"""
        return self.login_status.strip().lower() not in ("n", "no", "false")

    @property
    def display_name(self) -> str:
        parts = [self.case_id, self.module, self.interface_name]
        return "-".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _safe_json_parse(json_str: str, default: Any) -> Any:
    """安全解析 JSON 字符串。"""
    if not json_str or not str(json_str).strip():
        return default
    try:
        return json.loads(str(json_str).strip())
    except (json.JSONDecodeError, TypeError) as e:
        warning(f"JSON 解析失败: '{json_str}' -> {e}")
        return default


# ---------------------------------------------------------------------------
# 列名映射（中文 → 字段名）
# ---------------------------------------------------------------------------

_COLUMN_MAP: dict[str, str] = {
    "用例编号": "case_id",
    "接口名称": "interface_name",
    "请求URL": "url",
    "请求方法": "method",
    "请求头": "headers",
    "请求参数": "params",
    "预期结果": "expected_result",
    "替换变量标识": "replace_flag",
    "提取表达式": "extract_expression",
    "全局变量名": "global_var_name",
    "数据库校验SQL": "db_check_sql",
    "数据库预期值": "db_expected_value",
    "是否鉴权": "login_status",
    "是否启用": "enabled",
    "所属模块": "module",
    "备注": "remark",
}


# ---------------------------------------------------------------------------
# 核心加载函数
# ---------------------------------------------------------------------------

def load_excel_cases(file_name: str = "api_test_data.xlsx", sheet_name: str | None = None) -> list[ApiCaseData]:
    """
    加载 Excel 用例文件，返回 ApiCaseData 列表。

    Args:
        file_name: Excel 文件名（位于 TestDatas/ 目录下）
        sheet_name: 工作表名称，None 表示第一个工作表

    Returns:
        list[ApiCaseData]: 启用的测试用例列表
    """
    file_path: str = get_excel_path(file_name)

    if not file_path or not file_path.endswith(('.xlsx', '.xlsm')):
        raise FileNotFoundError(f"Excel 文件路径无效: {file_path}")

    import os
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Excel 用例文件不存在: {file_path}")

    info(f"加载 Excel 用例文件: {file_path}")

    workbook = openpyxl.load_workbook(file_path, read_only=True, data_only=True)

    if sheet_name:
        if sheet_name not in workbook.sheetnames:
            workbook.close()
            raise ValueError(f"工作表 '{sheet_name}' 不存在")
        ws = workbook[sheet_name]
    else:
        ws = workbook.active

    rows = list(ws.rows)
    workbook.close()

    if len(rows) < 2:
        raise ValueError(f"Excel 至少需要表头行和一行数据")

    # 解析表头
    header_row = rows[0]
    col_mapping: dict[int, str] = {}

    for col_idx, cell in enumerate(header_row):
        cell_value = str(cell.value).strip() if cell.value else ""
        if cell_value in _COLUMN_MAP:
            col_mapping[col_idx] = _COLUMN_MAP[cell_value]

    if not col_mapping:
        raise ValueError("Excel 表头未匹配到有效列名")

    info(f"解析到 {len(col_mapping)} 个有效列")

    # 解析数据行
    test_cases: list[ApiCaseData] = []

    for row in rows[1:]:
        row_data: dict[str, str] = {}
        for col_idx, field_name in col_mapping.items():
            cell_value = row[col_idx].value if col_idx < len(row) else None
            row_data[field_name] = str(cell_value).strip() if cell_value is not None else ""

        if not row_data.get("case_id") and not row_data.get("interface_name"):
            continue

        case = ApiCaseData(
            case_id=row_data.get("case_id", ""),
            interface_name=row_data.get("interface_name", ""),
            url=row_data.get("url", ""),
            method=row_data.get("method", "GET").upper(),
            headers=row_data.get("headers", ""),
            params=row_data.get("params", ""),
            expected_result=row_data.get("expected_result", ""),
            replace_flag=row_data.get("replace_flag", "N"),
            extract_expression=row_data.get("extract_expression", ""),
            global_var_name=row_data.get("global_var_name", ""),
            db_check_sql=row_data.get("db_check_sql", ""),
            db_expected_value=row_data.get("db_expected_value", ""),
            login_status=row_data.get("login_status", "Y"),
            enabled=row_data.get("enabled", "Y"),
            module=row_data.get("module", ""),
            remark=row_data.get("remark", ""),
        )

        if case.is_enabled:
            test_cases.append(case)
            info(f"加载用例: {case.display_name}")
        else:
            info(f"跳过禁用用例: {case.display_name}")

    info(f"共加载 {len(test_cases)} 条启用的测试用例")
    return test_cases
