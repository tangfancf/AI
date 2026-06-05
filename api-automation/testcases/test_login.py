"""
登录接口自动化测试用例

接口信息 (根据实际文档修改):
    - 路径: POST /api/login
    - 请求体: {"username": "xxx", "password": "xxx"}
    - 响应: {"code": 0, "msg": "success", "data": {"token": "xxx"}}
"""
import logging

import pytest

from common.assertions import assert_response
from common.data_loader import get_test_ids, load_test_cases
from common.http_client import HttpClient

logger = logging.getLogger(__name__)

# 加载测试数据
test_cases = load_test_cases("login.yaml")
test_ids = get_test_ids(test_cases)


class TestLogin:
    """登录接口测试"""

    @pytest.mark.parametrize("case", test_cases, ids=test_ids)
    def test_login(self, http_client: HttpClient, case: dict):
        """
        数据驱动的登录测试

        根据 YAML 中的测试数据自动执行多组测试
        """
        # Arrange
        input_data = case["input"]
        expected = case["expected"]

        # Act
        response = http_client.post(
            "/api/login",
            json_data={
                "username": input_data["username"],
                "password": input_data["password"],
            },
        )

        # Assert
        assertion = assert_response(response)
        assertion.status_code(expected["status_code"])

        if "code" in expected:
            assertion.json_field("$.code", expected["code"])

        if "msg" in expected:
            assertion.json_field("$.msg", expected["msg"])

    def test_login_returns_token(self, http_client: HttpClient):
        """登录成功后返回有效 token"""
        response = http_client.post(
            "/api/login",
            json_data={"username": "tangfan", "password": "P@ssw0rd"},
        )

        assert_response(response).status_code(200).json_field(
            "$.code", 0
        ).json_field_exists("$.data.token").json_field_not_empty("$.data.token")

    def test_login_response_time(self, http_client: HttpClient):
        """登录接口响应时间应在 3 秒内"""
        response = http_client.post(
            "/api/login",
            json_data={"username": "tangfan", "password": "P@ssw0rd"},
        )

        assert_response(response).response_time(3000)
