"""
conftest.py — 全局 Pytest Fixture 池

提供以下功能：
  - --project 命令行参数，支持多项目切换
  - requests_util: 创建 RequestsUtil 请求封装实例（基于 Session）
  - login_token: 自动登录并存储 Token 到全局变量

所有 Fixture 均为 Session 作用域。

使用方式：
  python3 main.py                           # 默认项目
  python3 main.py --project=jsonplaceholder # 指定项目
  pytest TestCases/ --project=httpbin -v -s
"""
from __future__ import annotations

import pytest
import requests

from Common.requests_util import RequestsUtil
from Common.global_data import GlobalData
from Common.log_util import info
from Common.ini_util import IniUtil
from Common.path_util import ensure_dirs
from Common.project_util import (
    get_project_config,
    get_default_project,
    show_available_projects,
)


def _get_current_project_name() -> str:
    """获取当前项目名称（从命令行参数或默认值）。"""
    project_name = get_default_project()
    try:
        import sys
        for arg in sys.argv:
            if arg.startswith("--project="):
                project_name = arg.split("=", 1)[1]
                break
    except Exception:
        pass
    return project_name


# ---------------------------------------------------------------------------
# pytest 命令行参数注册
# ---------------------------------------------------------------------------

def pytest_addoption(parser: pytest.Parser) -> None:
    """注册 --project 命令行参数。"""
    parser.addoption(
        "--project",
        action="store",
        default=None,
        help="指定测试项目名称，对应 projects.yaml 中的项目名",
    )


# ---------------------------------------------------------------------------
# 框架初始化
# ---------------------------------------------------------------------------

def pytest_configure(config: pytest.Config) -> None:
    """pytest 初始化钩子。"""
    ensure_dirs()

    project_name: str = config.getoption("--project", default=None) or get_default_project()
    project_cfg = get_project_config(project_name)

    info("=" * 60)
    info(f"ApiAutoTest 框架初始化 | 项目: {project_name}")
    info("=" * 60)

    show_available_projects()


# ---------------------------------------------------------------------------
# Fixture 定义
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def requests_util() -> RequestsUtil:
    """
    创建请求封装实例（Session 级别共享）。

    基于 requests.Session 实现：
      - 连接池复用
      - Cookie 自动管理
      - 统一公共请求头

    Returns:
        RequestsUtil: 请求封装实例
    """
    project_name = _get_current_project_name()
    config = get_project_config(project_name)
    base_url = config.get("base_url", "https://httpbin.org")
    timeout = IniUtil.get_int("api", "timeout", 10)
    util = RequestsUtil(base_url=base_url, timeout=timeout)
    info(f"[conftest] 请求封装初始化完成: base_url={base_url}")
    yield util
    # Session 结束时关闭连接池
    util.close()


@pytest.fixture(scope="session", autouse=True)
def login_token() -> None:
    """
    自动登录并存储 Token 到全局变量（Session 级别，自动执行）。

    执行流程：
      1. 请求登录接口
      2. 从响应中提取 Token
      3. 存入全局变量 GlobalData
      4. 后续接口根据 Excel 的「是否鉴权」列自动注入
    """
    project_name = _get_current_project_name()
    config = get_project_config(project_name)
    base_url = config.get("base_url", "https://httpbin.org")

    # 使用 Session 发送登录请求（保持会话状态）
    session = requests.Session()
    login_url = f"{base_url}/post"
    payload = {"username": "admin", "password": "123456"}

    try:
        response = session.post(login_url, json=payload, timeout=10)
        resp_json = response.json()

        # 从响应提取 token（httpbin 模拟环境使用默认值）
        token = resp_json.get("json", {}).get("token", "test-token-12345")

        # 存入全局变量
        GlobalData.set("login_token", token)
        info(f"[conftest] 登录成功，Token 已存入全局变量: login_token = {token}")

    except Exception as e:
        # 登录失败使用默认 Token，不阻塞测试
        GlobalData.set("login_token", "test-token-12345")
        info(f"[conftest] 登录异常，使用默认Token: {e}")
    finally:
        session.close()
