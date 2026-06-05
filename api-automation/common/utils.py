"""
通用工具函数
"""
import random
import string
import time
from typing import Any, Dict

from faker import Faker

fake = Faker("zh_CN")


def random_string(length: int = 8) -> str:
    """生成随机字符串"""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def random_phone() -> str:
    """生成随机手机号"""
    return fake.phone_number()


def random_email() -> str:
    """生成随机邮箱"""
    return fake.email()


def random_name() -> str:
    """生成随机中文姓名"""
    return fake.name()


def timestamp() -> int:
    """当前时间戳 (毫秒)"""
    return int(time.time() * 1000)


def replace_placeholders(data: Any, context: Dict[str, Any]) -> Any:
    """
    递归替换数据中的占位符变量

    支持格式: ${variable_name}

    Args:
        data: 待替换的数据 (支持 dict, list, str)
        context: 变量上下文 {"token": "xxx", "user_id": 123}

    Returns:
        替换后的数据

    Example:
        data = {"token": "${token}", "user_id": "${user_id}"}
        context = {"token": "abc123", "user_id": 42}
        result = replace_placeholders(data, context)
        # {"token": "abc123", "user_id": 42}
    """
    if isinstance(data, str):
        for key, value in context.items():
            placeholder = f"${{{key}}}"
            if data == placeholder:
                return value  # 完全匹配时保留原始类型
            data = data.replace(placeholder, str(value))
        return data
    elif isinstance(data, dict):
        return {k: replace_placeholders(v, context) for k, v in data.items()}
    elif isinstance(data, list):
        return [replace_placeholders(item, context) for item in data]
    return data
