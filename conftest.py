"""
conftest.py — 全局 Pytest Fixture 池

提供以下功能：
  - --project 命令行参数，支持多项目切换
  - requests_util: 创建 RequestsUtil 请求封装实例
  - login_token: 自动登录并存储 Token 到全局变量

所有 Fixture 均为 Session 作用域。

使用方式：
  # 默认项目（httpbin）
  python3 main.py

  # 指定项目
  python3 main.py --project=jsonplaceholder

  # pytest 直接运行
  python3 -m pytest TestCases/ --project=httpbin -v -s
"""
from __future__ import annotations

from typing import Any

import pytest
import requests

from Common.requests_util import RequestsUtil
from Common.global_data import GlobalData
from Common.log_util import info
from Common.ini_util import IniUtil
from Common.path_util import ensure_dirs


# ---------------------------------------------------------------------------
# 项目配置缓存（Session 级别，避免重复读取 INI）
# ---------------------------------------------------------------------------
_project_config: dict[str, str] = {}


def _get_project_config(project_name: str) -> dict[str, str]:
    """
    获取指定项目的配置信息。

    从 config.ini 的 [project_项目名] 节读取配置，
    如果项目节不存在则回退到默认 [api] 节。

    Args:
        project_name: 项目名称，如 httpbin、jsonplaceholder

    Returns:
        dict[str, str]: 项目配置，包含 excel_file、base_url 等
    """
    global _project_config

    if _project_config:
        return _project_config

    section = f"project_{project_name}"

    if IniUtil.get(section, "excel_file"):
        _project_config = {
            "excel_file": IniUtil.get(section, "excel_file", "api_test_data.xlsx"),
            "base_url": IniUtil.get(section, "base_url", "https://httpbin.org"),
            "description": IniUtil.get(section, "description", project_name),
        }
        info(f"[conftest] 使用项目配置: {section} → {_project_config}")
    else:
        # 回退到默认配置
        _project_config = {
            "excel_file": "api_test_data.xlsx",
            "base_url": IniUtil.get("api", "base_url", "https://httpbin.org"),
            "description": "默认项目",
        }
        info(f"[conftest] 项目节 [{section}] 不存在，使用默认配置")

    return _project_config


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
        default="httpbin",
        help="指定测试项目名称，对应 config.ini 中的 [project_项目名] 节",
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
      3. 初始化日志
    """
    ensure_dirs()

    # 获取项目名称并加载配置
    project_name: str = config.getoption("--project", default="httpbin")
    _get_project_config(project_name)

    info("=" * 60)
    info(f"ApiAutoTest 框架初始化 | 项目: {project_name}")
    info("=" * 60)


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
    config = _get_project_config("")
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
    config = _get_project_config("")
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
