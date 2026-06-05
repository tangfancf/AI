"""
Pytest 全局 fixtures 和配置
"""
import logging

import pytest

from common.http_client import HttpClient
from common.logger import setup_logging
from config.settings import get_auth, get_base_url

logger = logging.getLogger(__name__)


def pytest_configure(config):
    """pytest 初始化配置"""
    setup_logging()


@pytest.fixture(scope="session")
def http_client() -> HttpClient:
    """会话级 HTTP 客户端 (整个测试会话共享, 带 Cookie 认证)"""
    client = HttpClient()
    # 设置登录 Cookie
    client.session.headers.update({
        "Cookie": (
            "Hm_lvt_14752563c89f0870e93d2f6ac497f815=1778463007; "
            "jwtToken=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9."
            "eyJ0ZW5hbnRzIjpbImFkcyIsImFtcyIsImNjb3MiLCJjbXMiLCJjc3MiLCJlZGkiLCJmZWlzaHVoNSIsImhhaXRvdSIsImhlbGxvIiwiamlnb25namlhIiwibW1zIiwicW1zIiwicW1zIiwicmNzIiwic2NybSIsInVwbXMiLCJ5dXBhbyIsInl1cGFvZGFvamlhIiwieXVwYW9kYW9qaWEiXSwib3BlbklkIjoib3VfZTQ5MDQyNWZhYTNiNmQxNGVjYTJlYjU3NWZiNmVjNDEiLCJ1c2VyTmFtZSI6IuaxpOeVqiIsImV4cCI6MTc4MDk2OTY1NywidXNlcklkIjoiNjcyYjdnNmQifQ."
            "cdDLX1yyE4sn9-tu5BrYfxPdOwZKpKYrZxitBzqxPEk"
        ),
    })
    return client


@pytest.fixture(scope="session")
def auth_client() -> HttpClient:
    """
    带认证的 HTTP 客户端 (自动登录)

    登录逻辑需要根据实际接口调整:
    - 修改登录路径
    - 修改请求体字段
    - 修改 token 提取路径
    """
    client = HttpClient()
    auth_info = get_auth()

    # ===== 登录获取 token (根据实际接口修改) =====
    login_response = client.post(
        "/api/login",
        json_data={
            "username": auth_info["username"],
            "password": auth_info["password"],
        },
    )

    if login_response.status_code == 200:
        resp_json = login_response.json()
        # 根据实际响应结构提取 token
        token = resp_json.get("data", {}).get("token", "")
        if not token:
            token = resp_json.get("token", "")
        if token:
            client.token = token
            logger.info("✓ 登录成功，token 已设置")
        else:
            logger.warning("⚠ 登录响应中未找到 token")
    else:
        logger.error(f"✗ 登录失败，状态码: {login_response.status_code}")

    return client


@pytest.fixture(scope="function")
def context() -> dict:
    """
    测试上下文 - 用于在测试步骤间传递数据

    Example:
        def test_create_and_get(auth_client, context):
            # 创建
            resp = auth_client.post("/api/users", json_data={...})
            context["user_id"] = resp.json()["data"]["id"]

            # 查询
            resp = auth_client.get(f"/api/users/{context['user_id']}")
    """
    return {}
