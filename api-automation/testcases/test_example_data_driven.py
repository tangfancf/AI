"""
数据驱动示例 - 展示如何快速添加新接口的测试用例

使用方法:
1. 在 testdata/ 目录创建对应的 YAML 数据文件
2. 复制此模板, 修改接口路径和请求参数
3. 运行测试
"""
import logging

import pytest

from common.assertions import assert_response
from common.data_loader import get_test_ids, load_test_cases
from common.http_client import HttpClient
from common.utils import replace_placeholders

logger = logging.getLogger(__name__)


class TestDataDrivenExample:
    """
    数据驱动测试模板

    适用于以下场景:
    - 同一个接口需要验证多组输入/输出
    - 需要覆盖正常和异常用例
    - 参数组合测试
    """

    @pytest.fixture(autouse=True)
    def setup(self, auth_client: HttpClient, context: dict):
        """测试前置条件"""
        self.client = auth_client
        self.context = context

    @pytest.mark.parametrize(
        "case",
        load_test_cases("user_crud.yaml"),
        ids=get_test_ids(load_test_cases("user_crud.yaml")),
    )
    def test_with_yaml_data(self, case: dict):
        """
        YAML 数据驱动测试示例

        每个 case 包含:
        - case_id: 用例编号
        - title: 用例标题
        - input: 输入数据
        - expected: 预期结果
        """
        logger.info(f"执行用例: [{case['case_id']}] {case['title']}")

        # 替换变量占位符
        input_data = replace_placeholders(case["input"], self.context)
        expected = case["expected"]

        # 这里仅做演示, 实际使用时按具体接口调用
        logger.info(f"输入数据: {input_data}")
        logger.info(f"预期结果: {expected}")

        # 示例: 调用接口并断言
        # response = self.client.post("/api/xxx", json_data=input_data)
        # assert_response(response).status_code(expected["status_code"])
