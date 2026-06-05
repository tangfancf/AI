"""
用户 CRUD 接口自动化测试用例

接口信息 (根据实际文档修改):
    - 创建: POST /api/users
    - 查询: GET /api/users/{id}
    - 列表: GET /api/users?page=1&size=10
    - 更新: PUT /api/users/{id}
    - 删除: DELETE /api/users/{id}
"""
import logging

import pytest

from common.assertions import assert_response
from common.http_client import HttpClient
from common.utils import random_email, random_name, random_phone

logger = logging.getLogger(__name__)


class TestUserCRUD:
    """用户增删改查接口测试 - 完整业务流程"""

    def test_user_full_lifecycle(self, auth_client: HttpClient, context: dict):
        """
        用户完整生命周期测试:
        创建 -> 查询 -> 更新 -> 查询验证 -> 删除 -> 查询验证已删除
        """
        # ===== Step 1: 创建用户 =====
        create_data = {
            "username": f"auto_test_{random_phone()[-4:]}",
            "email": random_email(),
            "phone": random_phone(),
            "name": random_name(),
            "role": "user",
        }

        resp = auth_client.post("/api/users", json_data=create_data)
        assert_response(resp).status_code(200).json_field("$.code", 0)

        user_id = resp.json()["data"]["id"]
        context["user_id"] = user_id
        logger.info(f"创建用户成功, ID: {user_id}")

        # ===== Step 2: 查询用户 =====
        resp = auth_client.get(f"/api/users/{user_id}")
        assert_response(resp).status_code(200).json_field(
            "$.code", 0
        ).json_field("$.data.username", create_data["username"]).json_field(
            "$.data.email", create_data["email"]
        )
        logger.info("查询用户成功")

        # ===== Step 3: 更新用户 =====
        new_email = random_email()
        resp = auth_client.put(
            f"/api/users/{user_id}",
            json_data={"email": new_email, "name": "更新后的姓名"},
        )
        assert_response(resp).status_code(200).json_field("$.code", 0)
        logger.info("更新用户成功")

        # ===== Step 4: 查询验证更新 =====
        resp = auth_client.get(f"/api/users/{user_id}")
        assert_response(resp).status_code(200).json_field(
            "$.data.email", new_email
        ).json_field("$.data.name", "更新后的姓名")
        logger.info("验证更新成功")

        # ===== Step 5: 删除用户 =====
        resp = auth_client.delete(f"/api/users/{user_id}")
        assert_response(resp).status_code(200).json_field("$.code", 0)
        logger.info("删除用户成功")

        # ===== Step 6: 验证已删除 =====
        resp = auth_client.get(f"/api/users/{user_id}")
        # 根据实际接口逻辑, 可能返回 404 或 code != 0
        assert resp.status_code == 404 or resp.json().get("code") != 0
        logger.info("验证用户已删除")

    def test_user_list_pagination(self, auth_client: HttpClient):
        """用户列表分页查询"""
        resp = auth_client.get("/api/users", params={"page": 1, "size": 10})
        assert_response(resp).status_code(200).json_field(
            "$.code", 0
        ).json_field_exists("$.data.list").json_field_type(
            "$.data.list", list
        ).json_field_exists("$.data.total")

    def test_user_list_search(self, auth_client: HttpClient):
        """用户列表搜索"""
        resp = auth_client.get(
            "/api/users", params={"page": 1, "size": 10, "keyword": "tangfan"}
        )
        assert_response(resp).status_code(200).json_field("$.code", 0)

    def test_create_user_missing_required_field(self, auth_client: HttpClient):
        """创建用户-缺少必填字段"""
        resp = auth_client.post("/api/users", json_data={"email": random_email()})
        assert_response(resp).status_code(200).json_field("$.code", -1)

    def test_create_user_invalid_email(self, auth_client: HttpClient):
        """创建用户-无效邮箱格式"""
        resp = auth_client.post(
            "/api/users",
            json_data={
                "username": f"test_{random_phone()[-4:]}",
                "email": "invalid-email",
                "phone": random_phone(),
            },
        )
        assert_response(resp).status_code(200).json_field("$.code", -1)
