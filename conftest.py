"""
conftest.py — 全局 Pytest Fixture 池

提供以下 Session 级别 Fixture：
  - requests_util: 创建 RequestsUtil 请求封装实例
  - login_token: 自动登录并存储 Token 到全局变量

所有 Fixture 均为 Session 作用域。
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
# 框架初始化
# ---------------------------------------------------------------------------

def pytest_configure(config: pytest.Config) -> None:
    """pytest 初始化钩子，确保目录和日志就绪。"""
    ensure_dirs()
    info("=" * 60)
    info("ApiAutoTest 框架初始化")
    info("=" * 60)


# ---------------------------------------------------------------------------
# Fixture 定义
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def requests_util() -> RequestsUtil:
    """
    创建请求封装实例（Session 级别共享）。

    Returns:
        RequestsUtil: 请求封装实例
    """
    base_url = IniUtil.get("api", "base_url", "https://httpbin.org")
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
    base_url = IniUtil.get("api", "base_url", "https://httpbin.org")

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
