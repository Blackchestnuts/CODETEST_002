"""
conftest.py — 全局 Pytest Fixture 池

提供以下功能：
  - --project 命令行参数，支持多项目切换
  - requests_util: 创建 RequestsUtil 请求封装实例
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


# ---------------------------------------------------------------------------
# pytest 命令行参数注册
# ---------------------------------------------------------------------------

def pytest_addoption(parser: pytest.Parser) -> None:
    """
    注册 --project 命令行参数。

    使用方式：
      pytest --project=httpbin
      pytest --project=jsonplaceholder
    """
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
    """
    pytest 初始化钩子。

    执行：
      1. 确保输出目录存在
      2. 加载项目配置
      3. 显示可用项目列表
    """
    ensure_dirs()

    # 获取项目名称：优先命令行参数，其次默认项目
    project_name: str = config.getoption("--project", default=None) or get_default_project()

    # 加载项目配置并缓存
    project_cfg = get_project_config(project_name)

    info("=" * 60)
    info(f"ApiAutoTest 框架初始化 | 项目: {project_name}")
    info("=" * 60)

    # 显示可用项目
    show_available_projects()


# ---------------------------------------------------------------------------
# Fixture 定义
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def requests_util() -> RequestsUtil:
    """
    创建请求封装实例（Session 级别共享）。

    根据 --project 参数自动选择对应项目的 base_url。

    Returns:
        RequestsUtil: 请求封装实例
    """
    # 从 projects.yaml 获取当前项目的 base_url
    project_name = get_default_project()
    try:
        import sys
        for arg in sys.argv:
            if arg.startswith("--project="):
                project_name = arg.split("=", 1)[1]
                break
            elif arg == "--project" and sys.argv.index(arg) + 1 < len(sys.argv):
                project_name = sys.argv[sys.argv.index(arg) + 1]
                break
    except Exception:
        pass

    config = get_project_config(project_name)
    base_url = config.get("base_url", "https://httpbin.org")
    timeout = IniUtil.get_int("api", "timeout", 10)
    util = RequestsUtil(base_url=base_url, timeout=timeout)
    info(f"[conftest] 请求封装初始化完成: base_url={base_url}")
    return util


@pytest.fixture(scope="session", autouse=True)
def login_token() -> None:
    """
    自动登录并存储 Token 到全局变量（Session 级别，自动执行）。

    执行流程：
      1. 请求登录接口
      2. 从响应中提取 Token
      3. 存入全局变量 GlobalData，供后续 #login_token# 引用
    """
    project_name = get_default_project()
    try:
        import sys
        for arg in sys.argv:
            if arg.startswith("--project="):
                project_name = arg.split("=", 1)[1]
                break
    except Exception:
        pass

    config = get_project_config(project_name)
    base_url = config.get("base_url", "https://httpbin.org")

    # 模拟登录请求（httpbin.org/post 回显请求体）
    login_url = f"{base_url}/post"
    payload = {"username": "admin", "password": "123456"}

    try:
        response = requests.post(login_url, json=payload, timeout=10)
        resp_json = response.json()

        # 从响应提取 token（httpbin 模拟环境使用默认值）
        token = resp_json.get("json", {}).get("token", "test-token-12345")

        # 存入全局变量，供后续接口通过 #login_token# 引用
        GlobalData.set("login_token", token)
        info(f"[conftest] 登录成功，Token 已存入全局变量: login_token = {token}")

    except Exception as e:
        # 登录失败使用默认 Token，不阻塞测试
        GlobalData.set("login_token", "test-token-12345")
        info(f"[conftest] 登录异常，使用默认Token: {e}")
