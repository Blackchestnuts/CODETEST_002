"""
TestCases/test_business/test_business_flow.py — 端到端业务流测试

与单接口测试不同，业务流测试模拟真实用户操作路径：
  登录 → 浏览商品 → 加购物车 → 下单 → 查看订单

业务流测试特点：
  - 使用 @pytest.mark.business 标记
  - 关注接口串联，验证数据在接口间的正确传递
  - 每一步都提取关键数据供下一步使用
  - 不强求每步都断言，但关键节点必须验证
"""
from __future__ import annotations

import pytest
import requests

from Common.global_data import GlobalData
from Common.log_util import info
from Common.project_util import get_project_config, get_default_project


def _get_current_project() -> str:
    """获取当前项目名称。"""
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


def _get_project_base_url(project_name: str | None = None) -> str:
    """获取指定项目的 base_url。"""
    name = project_name or _get_current_project()
    config = get_project_config(name)
    return config.get("base_url", "https://httpbin.org")


@pytest.mark.business
class TestHttpbinAuthFlow:
    """
    httpbin 鉴权业务流测试。

    流程：获取Token → 使用Token访问鉴权接口 → 多参数查询 → 验证
    使用 requests.Session 保持会话，自动管理 Cookie。
    """

    @pytest.fixture(autouse=True)
    def setup_session(self) -> None:
        """初始化 Session。"""
        self.base_url = _get_project_base_url("httpbin")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        yield
        self.session.close()

    def test_httpbin_auth_flow(self) -> None:
        """
        httpbin 鉴权业务流测试。

        流程：获取Token → 使用Token访问鉴权接口 → 验证响应
        """
        # Step 1: 模拟登录获取Token
        login_url = f"{self.base_url}/post"
        login_data = {"username": "admin", "password": "123456"}

        info("=" * 50)
        info("业务流 Step1: 模拟登录获取Token")
        info("=" * 50)

        resp = self.session.post(login_url, json=login_data, timeout=10)
        assert resp.status_code == 200, f"登录失败: {resp.status_code}"

        # 从响应中提取token（httpbin回显模式）
        resp_json = resp.json()
        token = resp_json.get("json", {}).get("token", "flow-test-token")

        # 存入全局变量
        GlobalData.set("flow_token", token)
        info(f"  Step1 完成: 获取Token = {token}")

        # Step 2: 使用Token访问鉴权接口
        info("=" * 50)
        info("业务流 Step2: 使用Token访问鉴权接口")
        info("=" * 50)

        auth_url = f"{self.base_url}/post"
        auth_headers = {"Authorization": f"Bearer {token}"}
        auth_data = {"action": "get_user_info"}

        resp2 = self.session.post(auth_url, json=auth_data, headers=auth_headers, timeout=10)
        assert resp2.status_code == 200, f"鉴权请求失败: {resp2.status_code}"

        # 验证Token被正确传递
        resp2_json = resp2.json()
        actual_auth = resp2_json.get("headers", {}).get("Authorization", "")
        assert "Bearer" in actual_auth, f"Token未正确传递: {actual_auth}"
        info(f"  Step2 完成: Token验证通过, Authorization = {actual_auth}")

        # Step 3: 多参数查询验证
        info("=" * 50)
        info("业务流 Step3: 多参数查询验证")
        info("=" * 50)

        query_url = f"{self.base_url}/get"
        query_params = {"token": token, "action": "query"}

        resp3 = self.session.get(query_url, params=query_params, timeout=10)
        assert resp3.status_code == 200, f"查询失败: {resp3.status_code}"

        resp3_json = resp3.json()
        assert resp3_json.get("args", {}).get("token") == token
        info(f"  Step3 完成: 查询参数验证通过")

        info("=" * 50)
        info("httpbin 业务流测试全部通过！")
        info("=" * 50)


@pytest.mark.business
class TestJsonplaceholderFlow:
    """
    JSONPlaceholder 用户-帖子业务流测试。

    流程：获取用户列表 → 获取用户详情 → 获取用户帖子 → 创建新帖子 → 验证
    使用 requests.Session 保持会话，自动管理 Cookie。
    """

    @pytest.fixture(autouse=True)
    def setup_session(self) -> None:
        """初始化 Session。"""
        self.base_url = _get_project_base_url("jsonplaceholder")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        yield
        self.session.close()

    def test_jsonplaceholder_user_post_flow(self) -> None:
        """
        JSONPlaceholder 用户-帖子业务流测试。

        流程：获取用户列表 → 获取用户详情 → 获取用户帖子 → 创建新帖子 → 验证
        """
        # Step 1: 获取用户列表
        info("=" * 50)
        info("业务流 Step1: 获取用户列表")
        info("=" * 50)

        users_url = f"{self.base_url}/users"
        resp = self.session.get(users_url, timeout=10)
        assert resp.status_code == 200
        users = resp.json()
        assert len(users) > 0, "用户列表为空"
        user_id = users[0]["id"]
        info(f"  Step1 完成: 获取到 {len(users)} 个用户, 选取 userId={user_id}")

        # Step 2: 获取用户详情
        info("=" * 50)
        info("业务流 Step2: 获取用户详情")
        info("=" * 50)

        user_url = f"{self.base_url}/users/{user_id}"
        resp2 = self.session.get(user_url, timeout=10)
        assert resp2.status_code == 200
        user_name = resp2.json()["name"]
        info(f"  Step2 完成: 用户名 = {user_name}")

        # Step 3: 获取用户帖子
        info("=" * 50)
        info("业务流 Step3: 获取用户帖子")
        info("=" * 50)

        posts_url = f"{self.base_url}/users/{user_id}/posts"
        resp3 = self.session.get(posts_url, timeout=10)
        assert resp3.status_code == 200
        posts = resp3.json()
        assert len(posts) > 0, "帖子列表为空"
        info(f"  Step3 完成: 获取到 {len(posts)} 篇帖子")

        # Step 4: 创建新帖子
        info("=" * 50)
        info("业务流 Step4: 创建新帖子")
        info("=" * 50)

        create_url = f"{self.base_url}/posts"
        new_post = {
            "title": f"业务流测试帖子-{user_name}",
            "body": "这是通过业务流测试创建的帖子",
            "userId": user_id,
        }
        resp4 = self.session.post(create_url, json=new_post, timeout=10)
        assert resp4.status_code == 201, f"创建帖子失败: {resp4.status_code}"
        created = resp4.json()
        assert created["title"] == new_post["title"]
        info(f"  Step4 完成: 创建帖子成功, id={created['id']}")

        info("=" * 50)
        info("JSONPlaceholder 业务流测试全部通过！")
        info("=" * 50)
