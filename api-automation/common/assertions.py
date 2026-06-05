"""
断言工具模块 - 提供丰富的断言方法
"""
import logging
from typing import Any, Optional

from jsonpath_ng import parse as jsonpath_parse
from requests import Response

logger = logging.getLogger(__name__)


class ResponseAssert:
    """响应断言类 - 支持链式调用"""

    def __init__(self, response: Response):
        self.response = response
        self._json = None

    @property
    def json_body(self) -> dict:
        """懒加载 JSON 响应体"""
        if self._json is None:
            self._json = self.response.json()
        return self._json

    def status_code(self, expected: int) -> "ResponseAssert":
        """断言 HTTP 状态码"""
        actual = self.response.status_code
        assert actual == expected, (
            f"状态码断言失败: 期望 {expected}, 实际 {actual}"
        )
        logger.info(f"✓ 状态码断言通过: {actual}")
        return self

    def json_field(self, json_path: str, expected: Any) -> "ResponseAssert":
        """
        断言 JSON 字段值 (使用 JSONPath 表达式)

        Args:
            json_path: JSONPath 表达式, 如 "$.data.id" 或 "$.code"
            expected: 期望值
        """
        expression = jsonpath_parse(json_path)
        matches = expression.find(self.json_body)
        assert matches, f"JSONPath '{json_path}' 未匹配到任何值"
        actual = matches[0].value
        assert actual == expected, (
            f"字段断言失败: {json_path} 期望 {expected!r}, 实际 {actual!r}"
        )
        logger.info(f"✓ 字段断言通过: {json_path} == {expected!r}")
        return self

    def json_field_exists(self, json_path: str) -> "ResponseAssert":
        """断言 JSON 字段存在"""
        expression = jsonpath_parse(json_path)
        matches = expression.find(self.json_body)
        assert matches, f"字段不存在断言失败: {json_path} 未找到"
        logger.info(f"✓ 字段存在断言通过: {json_path}")
        return self

    def json_field_not_empty(self, json_path: str) -> "ResponseAssert":
        """断言 JSON 字段不为空"""
        expression = jsonpath_parse(json_path)
        matches = expression.find(self.json_body)
        assert matches, f"JSONPath '{json_path}' 未匹配到任何值"
        actual = matches[0].value
        assert actual is not None and actual != "" and actual != [] and actual != {}, (
            f"字段非空断言失败: {json_path} 值为 {actual!r}"
        )
        logger.info(f"✓ 字段非空断言通过: {json_path}")
        return self

    def json_field_type(self, json_path: str, expected_type: type) -> "ResponseAssert":
        """断言 JSON 字段类型"""
        expression = jsonpath_parse(json_path)
        matches = expression.find(self.json_body)
        assert matches, f"JSONPath '{json_path}' 未匹配到任何值"
        actual = matches[0].value
        assert isinstance(actual, expected_type), (
            f"类型断言失败: {json_path} 期望 {expected_type.__name__}, "
            f"实际 {type(actual).__name__}"
        )
        logger.info(f"✓ 类型断言通过: {json_path} is {expected_type.__name__}")
        return self

    def json_field_contains(self, json_path: str, expected: Any) -> "ResponseAssert":
        """断言 JSON 字段包含某值"""
        expression = jsonpath_parse(json_path)
        matches = expression.find(self.json_body)
        assert matches, f"JSONPath '{json_path}' 未匹配到任何值"
        actual = matches[0].value
        assert expected in actual, (
            f"包含断言失败: {json_path} 中未包含 {expected!r}"
        )
        logger.info(f"✓ 包含断言通过: {json_path} contains {expected!r}")
        return self

    def json_list_length(
        self, json_path: str, min_len: Optional[int] = None, max_len: Optional[int] = None
    ) -> "ResponseAssert":
        """断言 JSON 列表长度"""
        expression = jsonpath_parse(json_path)
        matches = expression.find(self.json_body)
        assert matches, f"JSONPath '{json_path}' 未匹配到任何值"
        actual = matches[0].value
        assert isinstance(actual, list), f"{json_path} 不是列表类型"
        length = len(actual)
        if min_len is not None:
            assert length >= min_len, (
                f"列表长度断言失败: {json_path} 长度 {length} < 最小 {min_len}"
            )
        if max_len is not None:
            assert length <= max_len, (
                f"列表长度断言失败: {json_path} 长度 {length} > 最大 {max_len}"
            )
        logger.info(f"✓ 列表长度断言通过: {json_path} length={length}")
        return self

    def response_time(self, max_ms: int) -> "ResponseAssert":
        """断言响应时间"""
        elapsed_ms = self.response.elapsed.total_seconds() * 1000
        assert elapsed_ms <= max_ms, (
            f"响应时间断言失败: {elapsed_ms:.0f}ms > {max_ms}ms"
        )
        logger.info(f"✓ 响应时间断言通过: {elapsed_ms:.0f}ms <= {max_ms}ms")
        return self

    def body_contains(self, text: str) -> "ResponseAssert":
        """断言响应体包含文本"""
        assert text in self.response.text, (
            f"响应体包含断言失败: 未找到 '{text}'"
        )
        logger.info(f"✓ 响应体包含断言通过: '{text}'")
        return self


def assert_response(response: Response) -> ResponseAssert:
    """创建响应断言对象 (工厂函数)"""
    return ResponseAssert(response)
