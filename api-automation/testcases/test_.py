"""
{ 接口自动化测试 (由 curl_to_test.py 自动生成)

接口信息:
    - 路径: GET {
    - Base URL: ://
    - 生成时间: 2026-06-04 17:21:55
"""
import logging

import pytest
import yaml

from common.assertions import assert_response
from common.data_loader import get_test_ids, load_test_cases, DATA_DIR
from common.http_client import HttpClient

logger = logging.getLogger(__name__)

# 加载测试数据
_data_file = ".yaml"
_all_data = None


def _load_data():
    global _all_data
    if _all_data is None:
        with open(DATA_DIR / _data_file, "r", encoding="utf-8") as f:
            _all_data = yaml.safe_load(f)
    return _all_data


def _get_cases():
    return _load_data()["test_cases"]


def _get_api_info():
    return _load_data()["api_info"]


test_cases = _get_cases()
test_ids = get_test_ids(test_cases)


class Test:
    """{ 接口测试"""

    @pytest.mark.parametrize("case", test_cases, ids=test_ids)
    def test_data_driven(self, http_client: HttpClient, case: dict):
        """
        数据驱动测试: 自动遍历所有测试用例
        """
        logger.info("=" * 50)
        logger.info(f"执行用例: [{case['case_id']}] {case['title']}")

        # 构造请求
        method = case.get("method", "GET")
        path = case.get("path", "{")
        headers = case.get("headers", {})
        cookies = case.get("cookies", {})
        body = case.get("body")
        expected = case["expected"]

        # 设置请求头
        request_headers = {}
        if headers:
            request_headers.update(headers)

        # 设置 Cookie
        if cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
            request_headers["Cookie"] = cookie_str

        # 发送请求
        api_info = _get_api_info()
        full_url = f"{api_info['base_url']}{path}"

        response = http_client.request(
            method=method,
            path=full_url,
            json_data=body if isinstance(body, dict) else None,
            data=body if not isinstance(body, dict) and body else None,
            headers=request_headers if request_headers else None,
        )

        # 断言
        assertion = assert_response(response)
        assertion.status_code(expected["status_code"])

        if "code" in expected:
            assertion.json_field("$.code", expected["code"])

        if "message" in expected:
            assertion.json_field("$.message", expected["message"])

        if "error" in expected:
            assertion.json_field("$.error", expected["error"])

        logger.info(f"用例 [{case['case_id']}] 执行完成, 响应码: {response.status_code}")

    def test_response_time(self, http_client: HttpClient):
        """接口响应时间应在 5 秒内"""
        api_info = _get_api_info()
        case = test_cases[0]  # 使用第一个正常用例
        headers = case.get("headers", {})
        cookies = case.get("cookies", {})
        body = case.get("body")

        request_headers = {}
        if headers:
            request_headers.update(headers)
        if cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
            request_headers["Cookie"] = cookie_str

        full_url = f"{api_info['base_url']}{case['path']}"
        response = http_client.request(
            method=case.get("method", "GET"),
            path=full_url,
            json_data=body if isinstance(body, dict) else None,
            headers=request_headers if request_headers else None,
        )
        assert_response(response).response_time(5000)
