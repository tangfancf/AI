"""
根据计划ID查询员工 接口自动化测试

接口信息:
    - 路径: POST /crm-task/v1/csTaskConfig/plus/queryStaffByPlanId
    - Content-Type: application/json
    - 认证: Cookie (jwtToken)
    - 请求体:
        {
            "planId": int,         # 调度计划ID
            "planCode": string,    # 调度计划编码
            "tenantId": int,       # 租户ID
            "groupId": int,        # 分组ID
            "staffFsIds": [string],# 员工飞书ID列表
            "staffName": string    # 员工姓名(模糊搜索)
        }
    - 响应结构:
        {
            "code": int,           # 业务状态码 (0=成功, 400=业务错误, 601=未登录)
            "message": string,     # 提示信息
            "askId": string,       # 请求追踪ID
            "data": any,           # 业务数据
            "error": bool          # 是否错误
        }
"""
import logging

import pytest

from common.assertions import assert_response
from common.data_loader import get_test_ids, load_test_cases
from common.http_client import HttpClient

logger = logging.getLogger(__name__)

# 接口路径
API_PATH = "/crm-task/v1/csTaskConfig/plus/queryStaffByPlanId"

# 加载测试数据
test_cases = load_test_cases("query_staff_by_plan_id.yaml")
test_ids = get_test_ids(test_cases)


class TestQueryStaffByPlanId:
    """根据计划ID查询员工接口测试"""

    # ==================== 数据驱动测试 ====================

    @pytest.mark.parametrize("case", test_cases, ids=test_ids)
    def test_query_staff_data_driven(self, http_client: HttpClient, case: dict):
        """
        数据驱动测试: 覆盖参数校验、不存在资源、边界值场景
        """
        logger.info(f"{'=' * 50}")
        logger.info(f"执行用例: [{case['case_id']}] {case['title']}")

        # Arrange
        input_data = case["input"]
        expected = case["expected"]

        # Act
        response = http_client.post(API_PATH, json_data=input_data)

        # Assert
        assertion = assert_response(response)
        assertion.status_code(expected["status_code"])

        if "code" in expected:
            assertion.json_field("$.code", expected["code"])

        if "message" in expected:
            assertion.json_field("$.message", expected["message"])

        if "error" in expected:
            assertion.json_field("$.error", expected["error"])

        # 通用结构验证
        assertion.json_field_exists("$.askId")

    # ==================== 独立用例: 接口响应结构验证 ====================

    def test_response_structure(self, http_client: HttpClient):
        """验证接口响应包含标准字段: code, message, askId, data, error"""
        response = http_client.post(
            API_PATH,
            json_data={"planId": 1},
        )

        assertion = assert_response(response)
        assertion.status_code(200)
        assertion.json_field_exists("$.code")
        assertion.json_field_exists("$.message")
        assertion.json_field_exists("$.askId")
        # data 字段存在 (即使为 null)
        resp_json = response.json()
        assert "data" in resp_json, "响应缺少 data 字段"
        assert "error" in resp_json, "响应缺少 error 字段"
        logger.info("✓ 响应结构完整: code, message, askId, data, error")

    # ==================== 独立用例: 性能测试 ====================

    def test_response_time_under_5s(self, http_client: HttpClient):
        """接口响应时间应在 5 秒内"""
        response = http_client.post(
            API_PATH,
            json_data={
                "planId": 1,
                "planCode": "",
                "tenantId": 0,
                "groupId": 0,
                "staffFsIds": [],
                "staffName": "",
            },
        )
        assert_response(response).response_time(5000)

    # ==================== 独立用例: 认证测试 ====================

    def test_no_auth_returns_601(self):
        """未携带 Cookie 应返回 601 用户需要登录"""
        # 创建无认证的客户端
        from common.http_client import HttpClient as Client
        no_auth_client = Client()

        response = no_auth_client.post(
            API_PATH,
            json_data={"planId": 1},
        )

        assert_response(response).status_code(200).json_field(
            "$.code", 601
        ).json_field("$.message", "用户需要登录")

    # ==================== 独立用例: Content-Type 异常 ====================

    def test_wrong_content_type(self, http_client: HttpClient):
        """Content-Type 为 text/plain 时验证服务端行为"""
        response = http_client.request(
            "POST",
            API_PATH,
            data='{"planId": 1}',
            headers={"Content-Type": "text/plain"},
        )
        # 服务端不应返回 500
        assert response.status_code != 500, (
            f"错误的 Content-Type 导致服务器 500: {response.text[:200]}"
        )
        logger.info(f"text/plain Content-Type 响应: code={response.json().get('code')}")

    # ==================== 独立用例: 参数缺失组合 ====================

    def test_only_plan_code_no_plan_id(self, http_client: HttpClient):
        """只传 planCode 不传 planId"""
        response = http_client.post(
            API_PATH,
            json_data={"planCode": "SOME_CODE"},
        )
        assert_response(response).status_code(200)
        resp_json = response.json()
        logger.info(f"只传planCode响应: code={resp_json['code']}, msg={resp_json['message']}")

    def test_only_staff_name(self, http_client: HttpClient):
        """只传 staffName 其他为空"""
        response = http_client.post(
            API_PATH,
            json_data={"staffName": "张三"},
        )
        assert_response(response).status_code(200)
        resp_json = response.json()
        # 应该提示缺少调度规则
        assert resp_json["code"] == 400, f"预期 code=400, 实际 code={resp_json['code']}"
        logger.info(f"只传staffName响应: code={resp_json['code']}, msg={resp_json['message']}")
