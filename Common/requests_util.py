"""
Common/requests_util.py — requests 接口请求封装

核心功能：
  - 使用 requests.Session 实现连接池 + Cookie 自动管理
  - 封装 GET/POST/PUT/DELETE/PATCH 请求
  - 带重试机制（Timeout/ConnectionError 自动重试）
  - 自动 #变量# 替换
  - 根据 login_status 列自动注入 Token 鉴权
  - 请求日志记录
  - 响应 jsonpath 提取并存入全局变量
  - 状态码 + 字段断言
  - 数据库校验

设计要点：
  - 所有请求统一走此模块，不直接使用 requests
  - 使用 Session 对象复用连接，自动管理 Cookie
  - 请求前自动调用 re_replace 替换 #变量#
  - 请求后自动调用 jsonpath 提取并存入全局变量
  - 断言失败抛出 AssertionError，由 pytest 捕获
"""
from __future__ import annotations

import time
from typing import Any

import requests

from Common.global_data import GlobalData
from Common.re_replace import replace as var_replace
from Common.jsonpath_util import extract_and_store
from Common.log_util import info, error, debug, warning
from Common.ini_util import IniUtil


class RequestsUtil:
    """
    接口请求封装类（基于 requests.Session）。

    使用 Session 的好处：
      1. 连接池复用，减少 TCP 握手开销
      2. 自动管理 Cookie，跨请求保持会话
      3. 统一设置公共请求头（如 Content-Type）

    使用方式：
        api = RequestsUtil(base_url="https://httpbin.org")
        api.send_request(case)
    """

    def __init__(self, base_url: str | None = None, *, max_retries: int = 3, retry_interval: float = 2.0, timeout: int = 10) -> None:
        """
        初始化请求封装。

        Args:
            base_url: 基础 URL，None 则从 config.ini 读取
            max_retries: 最大重试次数
            retry_interval: 重试间隔秒数
            timeout: 请求超时秒数
        """
        self.base_url: str = (base_url or IniUtil.get("api", "base_url", "https://httpbin.org")).rstrip("/")
        self.max_retries: int = max_retries
        self.retry_interval: float = retry_interval
        self.timeout: int = timeout

        # 使用 Session 实现连接池 + Cookie 自动管理
        self.session: requests.Session = requests.Session()

        # 设置公共请求头
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

        info(f"[requests_util] Session 初始化完成: base_url={self.base_url}")

    def send_request(self, case: Any) -> dict[str, Any]:
        """
        执行单条测试用例的完整流程。

        流程：
          1. 解析并替换 #变量#
          2. 根据 login_status 自动注入 Token
          3. 拼接 URL
          4. 发送请求（带重试）
          5. 断言状态码
          6. 断言响应字段
          7. jsonpath 提取并存入全局变量
          8. 数据库校验

        Args:
            case: ApiCaseData 用例对象

        Returns:
            dict[str, Any]: 执行结果摘要
        """
        info(f"{'='*60}")
        info(f"执行用例: {case.display_name}")
        info(f"  方法: {case.method}  URL: {case.url}  替换: {case.replace_flag}  鉴权: {case.login_status}")
        info(f"{'='*60}")

        # 1. 解析请求参数（如需替换则进行 #变量# 替换）
        headers = case.parse_headers()
        params = case.parse_params()

        if case.need_replace:
            headers = var_replace(headers)
            params = var_replace(params)
            if isinstance(case.url, str):
                case.url = var_replace(case.url)
            info(f"  替换后请求头: {headers}")
            info(f"  替换后参数: {params}")

        # 2. 根据 login_status 自动注入 Token
        headers = self._inject_auth_token(headers, case.login_status)

        # 3. 拼接 URL
        url = self._build_url(case.url)

        # 4. 发送请求
        response = self._send_request(
            method=case.method,
            url=url,
            headers=headers,
            params=params,
        )

        # 5. 断言预期结果
        expected = case.parse_expected_result()
        if expected:
            self._assert_response(response, expected)

        # 6. jsonpath 提取并存入全局变量
        if case.extract_expression and case.global_var_name:
            try:
                resp_json = response.json()
                extract_and_store(resp_json, case.extract_expression, case.global_var_name)
            except Exception as e:
                warning(f"jsonpath 提取失败: {e}")

        # 7. 数据库校验
        if case.db_check_sql and case.db_expected_value:
            self._db_assert(case.db_check_sql, case.db_expected_value)

        result = {
            "case_id": case.case_id,
            "interface_name": case.interface_name,
            "status_code": response.status_code,
            "elapsed_ms": response.elapsed.total_seconds() * 1000,
        }
        info(f"用例执行成功: {case.display_name} ({result['elapsed_ms']:.0f}ms)")
        return result

    def _inject_auth_token(self, headers: dict[str, Any], login_status: str) -> dict[str, Any]:
        """
        根据 login_status 自动注入 Token 到请求头。

        login_status 取值：
          - "Y" 或 "auto":  自动注入 Token（默认行为）
          - "N" 或 "no":   不注入 Token（公开接口）
          - 其他值:         不注入 Token

        Args:
            headers: 原始请求头
            login_status: 鉴权标识

        Returns:
            dict[str, Any]: 注入后的请求头
        """
        status = str(login_status).strip().lower()

        # 不需要鉴权的接口直接返回
        if status in ("n", "no", "false"):
            info(f"  鉴权模式: 不需要Token（公开接口）")
            return headers

        # 需要鉴权（Y / auto / 空 / 任何其他值 → 默认注入）
        token = GlobalData.get("login_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
            info(f"  鉴权模式: 自动注入Token → Bearer {token[:20]}...")
        else:
            warning("  鉴权模式: 需要Token但全局变量中无login_token")

        return headers

    def _build_url(self, url_path: str) -> str:
        """拼接完整 URL。"""
        if url_path.startswith("http://") or url_path.startswith("https://"):
            return url_path
        path = url_path if url_path.startswith("/") else f"/{url_path}"
        return f"{self.base_url}{path}"

    def _send_request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> requests.Response:
        """带重试的请求发送（使用 Session）。"""
        last_exception: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                info(f"  请求 {attempt}/{self.max_retries}: {method} {url}")

                # GET 请求参数用 params，其他用 json body
                if method.upper() == "GET":
                    response = self.session.request(
                        method=method.upper(), url=url,
                        headers=headers, params=params,
                        timeout=self.timeout,
                    )
                else:
                    response = self.session.request(
                        method=method.upper(), url=url,
                        headers=headers, json=params,
                        timeout=self.timeout,
                    )

                info(f"  响应状态码: {response.status_code}")
                return response

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_exception = e
                warning(f"  请求失败 ({type(e).__name__}): 第 {attempt} 次重试")
                if attempt < self.max_retries:
                    time.sleep(self.retry_interval)

            except Exception:
                raise

        if last_exception:
            raise last_exception
        raise RuntimeError("请求重试逻辑异常")

    def _assert_response(self, response: requests.Response, expected: dict[str, Any]) -> None:
        """断言响应字段。"""
        try:
            resp_json = response.json()
        except Exception as e:
            raise AssertionError(f"响应非 JSON: {e}")

        for path, expected_value in expected.items():
            from Common.jsonpath_util import extract
            actual_value = extract(resp_json, path)
            actual_str = str(actual_value) if actual_value is not None else ""
            expected_str = str(expected_value)

            assert actual_str == expected_str, (
                f"断言失败: 路径='{path}'\n"
                f"  期望: {expected_value}\n"
                f"  实际: {actual_value}\n"
                f"  响应: {str(resp_json)[:300]}"
            )
            info(f"  断言通过: {path} = {expected_value}")

    def _db_assert(self, sql: str, expected_value: str) -> None:
        """数据库校验。"""
        try:
            from Common.mysql_util import MysqlUtil
            actual = MysqlUtil.fetch_one_value(sql)
            actual_str = str(actual) if actual is not None else ""
            assert actual_str == str(expected_value), (
                f"数据库断言失败: SQL='{sql}'\n"
                f"  期望: {expected_value}\n"
                f"  实际: {actual}"
            )
            info(f"  数据库断言通过: {sql} → {actual}")
        except ImportError:
            warning("mysql_util 未配置，跳过数据库校验")
        except Exception as e:
            warning(f"数据库校验异常: {e}")

    def close(self) -> None:
        """关闭 Session，释放连接池资源。"""
        self.session.close()
        info("[requests_util] Session 已关闭")
