"""
测试数据加载器 - 支持 YAML/JSON 格式的数据驱动
"""
import json
import logging
from pathlib import Path
from typing import Any, List

import yaml

from config.settings import BASE_DIR

logger = logging.getLogger(__name__)

# 测试数据目录
DATA_DIR = BASE_DIR / "testdata"


def load_yaml(file_path: str) -> Any:
    """加载 YAML 文件"""
    path = Path(file_path) if Path(file_path).is_absolute() else DATA_DIR / file_path
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    logger.info(f"加载 YAML 数据: {path}")
    return data


def load_json(file_path: str) -> Any:
    """加载 JSON 文件"""
    path = Path(file_path) if Path(file_path).is_absolute() else DATA_DIR / file_path
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"加载 JSON 数据: {path}")
    return data


def load_test_cases(file_path: str) -> List[dict]:
    """
    加载测试用例数据 (用于参数化)

    数据格式:
    ```yaml
    test_cases:
      - case_id: "TC001"
        title: "正常登录"
        input:
          username: "admin"
          password: "123456"
        expected:
          status_code: 200
          code: 0
          msg: "success"
    ```

    Returns:
        List[dict]: 测试用例列表
    """
    if file_path.endswith(".yaml") or file_path.endswith(".yml"):
        data = load_yaml(file_path)
    elif file_path.endswith(".json"):
        data = load_json(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {file_path}")

    test_cases = data.get("test_cases", data)
    if isinstance(test_cases, list):
        return test_cases
    return [test_cases]


def get_test_ids(test_cases: List[dict]) -> List[str]:
    """从测试用例列表中提取用例 ID (用于 pytest 参数化命名)"""
    ids = []
    for case in test_cases:
        case_id = case.get("case_id", case.get("title", "unnamed"))
        ids.append(str(case_id))
    return ids
