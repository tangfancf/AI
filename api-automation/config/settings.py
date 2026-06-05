"""
配置管理模块 - 读取并管理项目配置
"""
import os
from pathlib import Path

import yaml

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 配置文件路径
CONFIG_FILE = BASE_DIR / "config" / "config.yaml"


def load_config() -> dict:
    """加载配置文件"""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def get_env_config() -> dict:
    """获取当前激活环境的配置"""
    config = load_config()
    active_env = config["env"]["active"]
    return config[active_env]


def get_base_url() -> str:
    """获取当前环境的 base_url"""
    return get_env_config()["base_url"]


def get_auth() -> dict:
    """获取当前环境的认证信息"""
    return get_env_config()["auth"]


def get_timeout() -> int:
    """获取请求超时时间"""
    return get_env_config().get("timeout", 30)
