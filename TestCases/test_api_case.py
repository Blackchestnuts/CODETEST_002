"""
TestCases/test_api_case.py — 数据驱动接口自动化测试

核心流程：
  1. conftest.py 提供 requests_util Fixture（Session 级别）
  2. pytest_generate_tests 钩子根据 --project 参数动态加载对应 Excel
  3. test_api_case 逐条执行用例：
     读取 Excel → 正则替换 → 发请求 → 断言 → jsonpath提取 → DB校验

多项目切换：
  pytest --project=httpbin           → 加载 api_test_data.xlsx
  pytest --project=jsonplaceholder   → 加载 user_api_cases.xlsx
"""
from __future__ import annotations

import pytest

from Common.excel_util import ApiCaseData, load_excel_cases
from Common.requests_util import RequestsUtil
from Common.log_util import info
from Common.project_util import (
    get_project_config,
    get_default_project,
)


# ---------------------------------------------------------------------------
# 动态参数化：pytest 钩子
# ---------------------------------------------------------------------------

def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """
    pytest 动态参数化钩子。

    当测试函数的参数中包含 "api_case" 时：
      1. 从 projects.yaml 获取指定项目的 Excel 文件名
      2. 加载对应 Excel 中的测试用例
      3. 将用例参数化为独立的测试用例
    """
    if "api_case" in metafunc.fixturenames:
        # 获取 --project 参数，未指定则使用默认项目
        project_name: str = metafunc.config.getoption("--project", default=None) or get_default_project()

        # 从 projects.yaml 获取 Excel 文件名
        project_cfg = get_project_config(project_name)
        excel_file = project_cfg.get("excel_file", "api_test_data.xlsx")

        info(f"[test_api_case] 项目: {project_name}, Excel: {excel_file}")

        # 加载对应 Excel 的用例
        cases: list[ApiCaseData] = load_excel_cases(file_name=excel_file)
        ids: list[str] = [case.display_name for case in cases]
        metafunc.parametrize("api_case", cases, ids=ids)


# ---------------------------------------------------------------------------
# 测试类
# ---------------------------------------------------------------------------

class TestApiCase:
    """
    数据驱动接口自动化测试类。

    固定执行流程：
      读取 Excel → 正则替换 → 发请求 → 断言 → jsonpath提取 → DB校验
    """

    def test_api_case(self, requests_util: RequestsUtil, api_case: ApiCaseData) -> None:
        """
        执行单条 Excel 驱动的接口测试用例。

        Args:
            requests_util: 请求封装实例
            api_case: 由参数化注入的单条测试用例

        Raises:
            AssertionError: 断言失败时抛出
        """
        requests_util.send_request(api_case)
