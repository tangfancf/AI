#!/usr/bin/env python3
"""
cURL 一键生成接口自动化测试用例并执行

使用方法:
    python curl_to_test.py "curl --location 'https://xxx.com/api/path' --header 'Content-Type: application/json' --data '{...}'"

功能:
    1. 解析 curl 命令 (支持 --location, --header, --data, --request 等)
    2. 自动生成测试数据文件 (testdata/xxx.yaml)
    3. 自动生成测试用例文件 (testcases/test_xxx.py)
    4. 执行测试并保存结果到 reports/ 目录
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent


def parse_curl(curl_command: str) -> Dict[str, Any]:
    """
    解析 curl 命令，提取请求信息

    Returns:
        {
            "method": "POST",
            "url": "https://xxx.com/api/path",
            "headers": {"Content-Type": "application/json", ...},
            "cookies": {"key": "value", ...},
            "body": {...} or None,
            "params": {...} or None,
        }
    """
    # 预处理: 合并多行反斜杠续行（包括 \ 后跟换行、\ 后跟空格换行等情况）
    curl_command = curl_command.replace("\\\r\n", " ").replace("\\\n", " ")

    # 处理 Windows 风格换行
    curl_command = curl_command.replace("\r\n", " ").replace("\n", " ")

    # 自动过滤所有残留的反斜杠（浏览器复制 curl 时常带有 \ 转义）
    # 1. 过滤行尾孤立的反斜杠（\ 后跟空格，通常是续行符残留）
    curl_command = re.sub(r"\\\s+", " ", curl_command)
    # 2. 过滤 \--header、\-H 等参数前的反斜杠（包括前面可能有空格的情况）
    curl_command = re.sub(r"\\(-{1,2})", r"\1", curl_command)
    # 3. 过滤单引号前的反斜杠 \'
    curl_command = curl_command.replace("\\'", "'")
    # 4. 过滤双引号前的反斜杠
    curl_command = curl_command.replace('\\"', '"')

    # 尝试用 shlex 分割
    try:
        tokens = shlex.split(curl_command)
    except ValueError:
        # 如果 shlex 失败，尝试手动处理
        curl_command = curl_command.replace("'", "'\"'\"'")
        tokens = shlex.split(curl_command)

    # 移除 'curl' 本身
    if tokens and tokens[0].lower() == "curl":
        tokens = tokens[1:]

    method = "GET"
    url = ""
    headers = {}
    cookies = {}
    body = None

    i = 0
    while i < len(tokens):
        token = tokens[i]

        if token in ("-X", "--request"):
            i += 1
            if i < len(tokens):
                method = tokens[i].upper()

        elif token in ("-H", "--header"):
            i += 1
            if i < len(tokens):
                header_str = tokens[i]
                if ":" in header_str:
                    key, value = header_str.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    if key.lower() == "cookie":
                        # 解析 Cookie
                        for part in value.split(";"):
                            part = part.strip()
                            if "=" in part:
                                ck, cv = part.split("=", 1)
                                cookies[ck.strip()] = cv.strip()
                    else:
                        headers[key] = value

        elif token in ("-d", "--data", "--data-raw", "--data-binary"):
            i += 1
            if i < len(tokens):
                method = method if method != "GET" else "POST"
                raw_body = tokens[i]
                try:
                    body = json.loads(raw_body)
                except (json.JSONDecodeError, TypeError):
                    body = raw_body

        elif token in ("-L", "--location", "--compressed", "-k", "--insecure"):
            pass  # 忽略这些标志

        elif token in ("-b", "--cookie"):
            i += 1
            if i < len(tokens):
                for part in tokens[i].split(";"):
                    part = part.strip()
                    if "=" in part:
                        ck, cv = part.split("=", 1)
                        cookies[ck.strip()] = cv.strip()

        elif not token.startswith("-") and not url:
            url = token

        i += 1

    # 如果有 body 但没有显式指定 method，则为 POST
    if body and method == "GET":
        method = "POST"

    return {
        "method": method,
        "url": url,
        "headers": headers,
        "cookies": cookies,
        "body": body,
    }


def extract_api_info(parsed: Dict[str, Any]) -> Dict[str, str]:
    """从解析结果中提取接口信息"""
    url = parsed["url"]
    parsed_url = urlparse(url)
    path = parsed_url.path
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # 从路径生成文件名
    # /crm-task/v1/csTaskConfig/plus/saveConfig -> save_config
    path_parts = [p for p in path.split("/") if p]
    if path_parts:
        # 取最后一个有意义的部分作为名称
        api_name = path_parts[-1]
        # 驼峰转下划线
        api_name = re.sub(r"([A-Z])", r"_\1", api_name).lower().strip("_")
        # 清理特殊字符
        api_name = re.sub(r"[^a-z0-9_]", "_", api_name)
        api_name = re.sub(r"_+", "_", api_name).strip("_")
    else:
        api_name = "api_test"

    return {
        "api_name": api_name,
        "api_path": path,
        "base_url": base_url,
        "method": parsed["method"],
    }


def generate_test_cases(parsed: Dict[str, Any], api_info: Dict[str, str]) -> List[Dict]:
    """根据解析的请求信息，生成多组测试用例"""
    cases = []
    body = parsed["body"]
    method = parsed["method"]
    headers = _filter_important_headers(parsed["headers"])
    cookies = parsed["cookies"]
    api_path = api_info["api_path"]
    prefix = api_info["api_name"].upper()

    # ===== 正向场景 =====

    # 正向场景-全参数有效 (使用原始数据)
    cases.append({
        "case_id": f"{prefix}_001",
        "title": "正向场景-全参数有效",
        "method": method,
        "path": api_path,
        "headers": headers,
        "cookies": cookies,
        "body": body,
        "expected": {
            "status_code": 200,
        },
    })

    if body and isinstance(body, dict) and method in ("POST", "PUT", "PATCH"):
        # 正向场景-仅必填字段（保留前3个字段作为必填字段的近似）
        required_fields = list(body.keys())[:3]
        if required_fields:
            required_body = {k: body[k] for k in required_fields if k in body}
            cases.append({
                "case_id": f"{prefix}_002",
                "title": "正向场景-仅必填字段",
                "method": method,
                "path": api_path,
                "headers": headers,
                "cookies": cookies,
                "body": required_body,
                "expected": {
                    "status_code": 200,
                },
            })

        # 业务变体（修改部分字段值为合法但不同的值）
        variant_body = dict(body)
        for k, v in variant_body.items():
            if isinstance(v, str) and v:
                variant_body[k] = v + "_variant"
                break
            elif isinstance(v, int):
                variant_body[k] = v + 1
                break
            elif isinstance(v, float):
                variant_body[k] = v + 0.1
                break
        cases.append({
            "case_id": f"{prefix}_003",
            "title": "业务变体",
            "method": method,
            "path": api_path,
            "headers": headers,
            "cookies": cookies,
            "body": variant_body,
            "expected": {
                "status_code": 200,
            },
        })

        # ===== 异常场景-缺少必填字段 =====
        field_idx = 4
        for key in list(body.keys())[:3]:  # 最多取前3个字段
            partial_body = {k: v for k, v in body.items() if k != key}
            cases.append({
                "case_id": f"{prefix}_{field_idx:03d}",
                "title": f"异常场景-缺少必填字段-{key}",
                "method": method,
                "path": api_path,
                "headers": headers,
                "cookies": cookies,
                "body": partial_body,
                "expected": {
                    "status_code": 200,
                },
            })
            field_idx += 1

        # ===== 类型转换测试 =====
        # 找到数值类型字段，传入字符串
        num_fields = [k for k, v in body.items() if isinstance(v, (int, float))]
        if num_fields:
            type_body = dict(body)
            type_body[num_fields[0]] = "abc_string"
            cases.append({
                "case_id": f"{prefix}_TYPE_STR",
                "title": "类型转换测试-传入字符串",
                "method": method,
                "path": api_path,
                "headers": headers,
                "cookies": cookies,
                "body": type_body,
                "expected": {
                    "status_code": 200,
                },
            })

        # ===== 空值测试 =====
        # 空值测试-请求体为null
        cases.append({
            "case_id": f"{prefix}_NULL_BODY",
            "title": "空值测试-请求体为null",
            "method": method,
            "path": api_path,
            "headers": headers,
            "cookies": cookies,
            "body": None,
            "expected": {
                "status_code": 200,
            },
        })

        # 空值测试-字段为null（将第一个字段设为null）
        null_field_body = dict(body)
        first_key = list(null_field_body.keys())[0]
        null_field_body[first_key] = None
        cases.append({
            "case_id": f"{prefix}_NULL_FIELD",
            "title": "空值测试-字段为null",
            "method": method,
            "path": api_path,
            "headers": headers,
            "cookies": cookies,
            "body": null_field_body,
            "expected": {
                "status_code": 200,
            },
        })

        # 空值测试-空对象
        cases.append({
            "case_id": f"{prefix}_EMPTY_OBJ",
            "title": "空值测试-空对象",
            "method": method,
            "path": api_path,
            "headers": headers,
            "cookies": cookies,
            "body": {},
            "expected": {
                "status_code": 200,
            },
        })

        # ===== 边界测试 =====
        if num_fields:
            # 边界测试-零值
            zero_body = dict(body)
            zero_body[num_fields[0]] = 0
            cases.append({
                "case_id": f"{prefix}_BOUND_ZERO",
                "title": "边界测试-零值",
                "method": method,
                "path": api_path,
                "headers": headers,
                "cookies": cookies,
                "body": zero_body,
                "expected": {
                    "status_code": 200,
                },
            })

            # 边界测试-负数
            neg_body = dict(body)
            neg_body[num_fields[0]] = -1
            cases.append({
                "case_id": f"{prefix}_BOUND_NEG",
                "title": "边界测试-负数",
                "method": method,
                "path": api_path,
                "headers": headers,
                "cookies": cookies,
                "body": neg_body,
                "expected": {
                    "status_code": 200,
                },
            })

            # 边界测试-极大值
            max_body = dict(body)
            max_body[num_fields[0]] = 9999999999999
            cases.append({
                "case_id": f"{prefix}_BOUND_MAX",
                "title": "边界测试-极大值",
                "method": method,
                "path": api_path,
                "headers": headers,
                "cookies": cookies,
                "body": max_body,
                "expected": {
                    "status_code": 200,
                },
            })

        # ===== 复杂类型测试 =====
        # 找到列表/字典类型字段，传入字符串
        complex_fields = [k for k, v in body.items() if isinstance(v, (list, dict))]
        if complex_fields:
            # 复杂类型测试-传入字符串
            complex_str_body = dict(body)
            complex_str_body[complex_fields[0]] = "invalid_string"
            cases.append({
                "case_id": f"{prefix}_COMPLEX_STR",
                "title": "复杂类型测试-传入字符串",
                "method": method,
                "path": api_path,
                "headers": headers,
                "cookies": cookies,
                "body": complex_str_body,
                "expected": {
                    "status_code": 200,
                },
            })

            # 复杂类型测试-非数字字符串
            complex_nan_body = dict(body)
            complex_nan_body[complex_fields[0]] = "not_a_number_xyz"
            cases.append({
                "case_id": f"{prefix}_COMPLEX_NAN",
                "title": "复杂类型测试-非数字字符串",
                "method": method,
                "path": api_path,
                "headers": headers,
                "cookies": cookies,
                "body": complex_nan_body,
                "expected": {
                    "status_code": 200,
                },
            })
        else:
            # 如果没有复杂类型字段，对数值字段传入非数字字符串
            if num_fields:
                complex_nan_body = dict(body)
                complex_nan_body[num_fields[0]] = "not_a_number_xyz"
                cases.append({
                    "case_id": f"{prefix}_COMPLEX_NAN",
                    "title": "复杂类型测试-非数字字符串",
                    "method": method,
                    "path": api_path,
                    "headers": headers,
                    "cookies": cookies,
                    "body": complex_nan_body,
                    "expected": {
                        "status_code": 200,
                    },
                })

    # ===== 安全测试-未授权访问 =====
    # 移除 headers 中所有认证相关字段（Authorization, token, Cookie 等）
    no_auth_headers = {
        k: v for k, v in headers.items()
        if k.lower() not in ("authorization", "token", "x-token", "x-access-token", "cookie")
    }
    cases.append({
        "case_id": f"{prefix}_NO_AUTH",
        "title": "【安全测试】未授权访问-无token或cookie访问",
        "method": method,
        "path": api_path,
        "headers": no_auth_headers,
        "cookies": {},
        "body": body,
        "expected": {
            "status_code": 200,
        },
    })

    # ===== 安全测试用例 =====
    if body and isinstance(body, dict) and method in ("POST", "PUT", "PATCH"):
        security_cases = _generate_security_cases(parsed, api_info, body)
        cases.extend(security_cases)

    return cases


def _generate_security_cases(parsed: Dict[str, Any], api_info: Dict[str, str], body: Dict) -> List[Dict]:
    """生成安全测试用例：SQL注入、盲注、XSS、水平越权、Header注入、批量遍历、参数类型/边界等"""
    cases = []
    method = parsed["method"]
    headers = _filter_important_headers(parsed["headers"])
    cookies = parsed["cookies"]
    api_path = api_info["api_path"]
    prefix = api_info["api_name"].upper()

    # 获取第一个字符串字段用于注入测试
    str_fields = [k for k, v in body.items() if isinstance(v, (str, int, float))]
    first_field = str_fields[0] if str_fields else list(body.keys())[0]

    # 获取ID类字段用于越权/遍历测试
    id_fields = [k for k in body.keys() if "id" in k.lower() or "Id" in k]
    id_field = id_fields[0] if id_fields else first_field

    def _make_case(case_id: str, title: str, injected_body, custom_headers=None, custom_cookies=None) -> Dict:
        return {
            "case_id": case_id,
            "title": title,
            "method": method,
            "path": api_path,
            "headers": custom_headers if custom_headers is not None else headers,
            "cookies": custom_cookies if custom_cookies is not None else cookies,
            "body": injected_body,
            "expected": {"status_code": 200},
        }

    def _inject_field(payload, field=None) -> Dict:
        """将 payload 注入到 body 的指定字段中"""
        injected = dict(body)
        injected[field or first_field] = payload
        return injected

    # --- 【安全测试】SQL注入-盲注 ---
    blind_payloads = [
        ("BLIND_001", "【安全测试】SQL注入-盲注-布尔盲注", "' AND '1'='1"),
        ("BLIND_002", "【安全测试】SQL注入-盲注-时间盲注", "'; WAITFOR DELAY '0:0:5'--"),
        ("BLIND_003", "【安全测试】SQL注入-盲注-报错注入", "' AND extractvalue(1,concat(0x7e,(SELECT version()),0x7e))--"),
        ("BLIND_004", "【安全测试】SQL注入-盲注-单引号闭合", "' OR '1'='1"),
        ("BLIND_005", "【安全测试】SQL注入-盲注-注释符截断", "'; DROP TABLE users;--"),
    ]
    for suffix, title, payload in blind_payloads:
        cases.append(_make_case(f"{prefix}_{suffix}", title, _inject_field(payload)))

    # --- 【安全测试】水平越权 ---
    # 使用其他用户的ID尝试访问
    horiz_body = dict(body)
    if id_field in horiz_body:
        original_id = horiz_body[id_field]
        if isinstance(original_id, int):
            horiz_body[id_field] = original_id + 99999
        elif isinstance(original_id, str):
            horiz_body[id_field] = "other_user_id_999"
        else:
            horiz_body[id_field] = "other_user_id_999"
    else:
        horiz_body[first_field] = "other_user_id_999"
    cases.append(_make_case(f"{prefix}_HORIZ_001", "【安全测试】水平越权", horiz_body))

    # --- 【安全测试】XSS攻击 ---
    xss_payloads = [
        ("XSS_001", "【安全测试】XSS攻击-script标签", "<script>alert('XSS')</script>"),
        ("XSS_002", "【安全测试】XSS攻击-事件处理器", "<img src=x onerror=alert('XSS')>"),
        ("XSS_003", "【安全测试】XSS攻击-编码绕过", "%3Cscript%3Ealert('XSS')%3C/script%3E"),
    ]
    for suffix, title, payload in xss_payloads:
        cases.append(_make_case(f"{prefix}_{suffix}", title, _inject_field(payload)))

    # --- 【安全测试】Header注入-X-Forwarded-For伪造IP ---
    forged_ip_headers = dict(headers)
    forged_ip_headers["X-Forwarded-For"] = "127.0.0.1"
    cases.append(_make_case(
        f"{prefix}_HDR_XFF",
        "【安全测试】Header注入-X-Forwarded-For伪造IP",
        body,
        custom_headers=forged_ip_headers,
    ))

    # --- 【安全测试】Header注入-User-Agent恶意工具检测 ---
    ua_headers = dict(headers)
    ua_headers["User-Agent"] = "sqlmap/1.5#stable (http://sqlmap.org)"
    cases.append(_make_case(
        f"{prefix}_HDR_UA",
        "【安全测试】Header注入-User-Agent恶意工具检测",
        body,
        custom_headers=ua_headers,
    ))

    # --- 【安全测试】批量遍历 ---
    # 尝试遍历ID（连续ID访问）
    batch_body = dict(body)
    if id_field in batch_body:
        original_id = batch_body[id_field]
        if isinstance(original_id, int):
            batch_body[id_field] = original_id + 1
        elif isinstance(original_id, str) and original_id.isdigit():
            batch_body[id_field] = str(int(original_id) + 1)
        else:
            batch_body[id_field] = "1"
    else:
        batch_body[first_field] = "1"
    cases.append(_make_case(f"{prefix}_BATCH_001", "【安全测试】批量遍历", batch_body))

    # --- 【安全测试】参数类型 ---
    # 对数值字段传入各种非法类型
    param_type_payloads = [
        ("PTYPE_001", "【安全测试】参数类型-数组代替字符串", [1, 2, 3]),
        ("PTYPE_002", "【安全测试】参数类型-对象代替字符串", {"key": "value"}),
        ("PTYPE_003", "【安全测试】参数类型-布尔值代替字符串", True),
    ]
    for suffix, title, payload in param_type_payloads:
        cases.append(_make_case(f"{prefix}_{suffix}", title, _inject_field(payload)))

    # --- 【安全测试】参数边界 ---
    param_bound_payloads = [
        ("PBOUND_001", "【安全测试】参数边界-超长字符串1024", "A" * 1024),
        ("PBOUND_002", "【安全测试】参数边界-超长字符串10000", "B" * 10000),
        ("PBOUND_003", "【安全测试】参数边界-特殊字符组合", "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"),
        ("PBOUND_004", "【安全测试】参数边界-空字符串", ""),
    ]
    for suffix, title, payload in param_bound_payloads:
        cases.append(_make_case(f"{prefix}_{suffix}", title, _inject_field(payload)))

    # --- UNION注入 ---
    union_payloads = [
        ("UNION_001", "安全-UNION注入-列数探测", "' UNION SELECT NULL,NULL,NULL--"),
        ("UNION_002", "安全-UNION注入-信息泄露", "0 UNION SELECT table_name,column_name FROM information_schema.columns--"),
    ]
    for suffix, title, payload in union_payloads:
        cases.append(_make_case(f"{prefix}_{suffix}", title, _inject_field(payload)))

    # --- 命令注入 ---
    cmd_payloads = [
        ("CMD_001", "安全-命令注入-管道符执行", "|ls -la /etc/passwd"),
        ("CMD_002", "安全-命令注入-反引号执行", "`cat /etc/passwd`"),
        ("CMD_003", "安全-命令注入-$()语法", "$(whoami)"),
    ]
    for suffix, title, payload in cmd_payloads:
        cases.append(_make_case(f"{prefix}_{suffix}", title, _inject_field(payload)))

    # --- 超长字符 ---
    cases.append(_make_case(
        f"{prefix}_LONG_001",
        "边界-超长字符串-1024字符",
        _inject_field("A" * 1024),
    ))
    cases.append(_make_case(
        f"{prefix}_LONG_002",
        "边界-超长字符串-10000字符",
        _inject_field("B" * 10000),
    ))

    # --- 中文字符 ---
    cn_payloads = [
        ("CN_001", "边界-中文字符-常规中文", "测试中文字符输入内容一二三四五六七八九十"),
        ("CN_002", "边界-中文字符-特殊符号", "测试！@#￥%……&*（）——+【】{}|；'：""《》？，。、"),
        ("CN_003", "边界-中文字符-emoji和特殊字符", "🔥💀👻测试emoji™®©℃①②③㊀㊁㊂"),
    ]
    for suffix, title, payload in cn_payloads:
        cases.append(_make_case(f"{prefix}_{suffix}", title, _inject_field(payload)))

    return cases


def _filter_important_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """过滤出重要的业务请求头（去掉浏览器自动添加的无关头）"""
    skip_headers = {
        "accept", "accept-language", "accept-encoding", "connection",
        "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site",
        "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",
        "user-agent", "origin", "referer",
    }
    result = {}
    for k, v in headers.items():
        if k.lower() not in skip_headers:
            result[k] = v
    return result


def generate_yaml_file(cases: List[Dict], api_info: Dict[str, str]) -> str:
    """生成测试数据 YAML 文件"""
    import yaml

    yaml_data = {
        "api_info": {
            "name": api_info["api_name"],
            "method": api_info["method"],
            "path": api_info["api_path"],
            "base_url": api_info["base_url"],
        },
        "test_cases": cases,
    }

    file_name = f"{api_info['api_name']}.yaml"
    file_path = BASE_DIR / "testdata" / file_name

    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(yaml_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return str(file_path)


def generate_test_file(api_info: Dict[str, str], yaml_file_name: str) -> str:
    """生成 pytest 测试用例文件"""
    api_name = api_info["api_name"]
    class_name = "".join(word.capitalize() for word in api_name.split("_"))
    test_file_name = f"test_{api_name}.py"
    test_file_path = BASE_DIR / "testcases" / test_file_name

    method = api_info["method"]
    api_path = api_info["api_path"]
    base_url = api_info["base_url"]
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        '"""',
        f'{api_path} 接口自动化测试 (由 curl_to_test.py 自动生成)',
        '',
        '接口信息:',
        f'    - 路径: {method} {api_path}',
        f'    - Base URL: {base_url}',
        f'    - 生成时间: {gen_time}',
        '"""',
        'import logging',
        '',
        'import pytest',
        'import yaml',
        '',
        'from common.assertions import assert_response',
        'from common.data_loader import get_test_ids, load_test_cases, DATA_DIR',
        'from common.http_client import HttpClient',
        '',
        'logger = logging.getLogger(__name__)',
        '',
        '# 加载测试数据',
        f'_data_file = "{yaml_file_name}"',
        '_all_data = None',
        '',
        '',
        'def _load_data():',
        '    global _all_data',
        '    if _all_data is None:',
        '        with open(DATA_DIR / _data_file, "r", encoding="utf-8") as f:',
        '            _all_data = yaml.safe_load(f)',
        '    return _all_data',
        '',
        '',
        'def _get_cases():',
        '    return _load_data()["test_cases"]',
        '',
        '',
        'def _get_api_info():',
        '    return _load_data()["api_info"]',
        '',
        '',
        'test_cases = _get_cases()',
        'test_ids = get_test_ids(test_cases)',
        '',
        '',
        f'class Test{class_name}:',
        f'    """{api_path} 接口测试"""',
        '',
        '    @pytest.mark.parametrize("case", test_cases, ids=test_ids)',
        '    def test_data_driven(self, http_client: HttpClient, case: dict):',
        '        """',
        '        数据驱动测试: 自动遍历所有测试用例',
        '        """',
        '        logger.info("=" * 50)',
        '        logger.info(f"执行用例: [{case[\'case_id\']}] {case[\'title\']}")',
        '',
        '        # 构造请求',
        f'        method = case.get("method", "{method}")',
        f'        path = case.get("path", "{api_path}")',
        '        headers = case.get("headers", {})',
        '        cookies = case.get("cookies", {})',
        '        body = case.get("body")',
        '        expected = case["expected"]',
        '',
        '        # 设置请求头',
        '        request_headers = {}',
        '        if headers:',
        '            request_headers.update(headers)',
        '',
        '        # 设置 Cookie',
        '        if cookies:',
        '            cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())',
        '            request_headers["Cookie"] = cookie_str',
        '',
        '        # 发送请求',
        '        api_info = _get_api_info()',
        '        full_url = f"{api_info[\'base_url\']}{path}"',
        '',
        '        response = http_client.request(',
        '            method=method,',
        '            path=full_url,',
        '            json_data=body if isinstance(body, dict) else None,',
        '            data=body if not isinstance(body, dict) and body else None,',
        '            headers=request_headers if request_headers else None,',
        '        )',
        '',
        '        # 断言',
        '        assertion = assert_response(response)',
        '        assertion.status_code(expected["status_code"])',
        '',
        '        if "code" in expected:',
        '            assertion.json_field("$.code", expected["code"])',
        '',
        '        if "message" in expected:',
        '            assertion.json_field("$.message", expected["message"])',
        '',
        '        if "error" in expected:',
        '            assertion.json_field("$.error", expected["error"])',
        '',
        '        logger.info(f"用例 [{case[\'case_id\']}] 执行完成, 响应码: {response.status_code}")',
        '',
        '    def test_response_time(self, http_client: HttpClient):',
        '        """接口响应时间应在 5 秒内"""',
        '        api_info = _get_api_info()',
        '        case = test_cases[0]  # 使用第一个正常用例',
        '        headers = case.get("headers", {})',
        '        cookies = case.get("cookies", {})',
        '        body = case.get("body")',
        '',
        '        request_headers = {}',
        '        if headers:',
        '            request_headers.update(headers)',
        '        if cookies:',
        '            cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())',
        '            request_headers["Cookie"] = cookie_str',
        '',
        '        full_url = f"{api_info[\'base_url\']}{case[\'path\']}"',
        '        response = http_client.request(',
        f'            method=case.get("method", "{method}"),',
        '            path=full_url,',
        '            json_data=body if isinstance(body, dict) else None,',
        '            headers=request_headers if request_headers else None,',
        '        )',
        '        assert_response(response).response_time(5000)',
        '',
    ]

    test_file_path.write_text("\n".join(lines), encoding="utf-8")
    return str(test_file_path)


def run_tests(test_file_path: str) -> Tuple[int, str, str]:
    """执行测试并保存结果，返回 (退出码, 报告路径, pytest输出)"""
    reports_dir = BASE_DIR / "reports"
    reports_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = reports_dir / f"report_{timestamp}.txt"

    # 运行 pytest
    cmd = [
        sys.executable, "-m", "pytest",
        test_file_path,
        "-v",
        "--tb=short",
        f"--junitxml={reports_dir / f'result_{timestamp}.xml'}",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR),
    )

    # 合并 stdout 和 stderr
    output = result.stdout + "\n" + result.stderr

    # 保存报告
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"测试执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"测试文件: {test_file_path}\n")
        f.write(f"{'=' * 60}\n\n")
        f.write(output)

    return result.returncode, str(report_file), output


def _parse_pytest_results(pytest_output: str) -> Dict[str, str]:
    """
    从 pytest -v 输出中解析每个用例的执行结果
    返回 {用例标识: "PASSED"/"FAILED"/...}
    """
    results = {}
    lines = pytest_output.splitlines()
    current_case_id = None

    for line in lines:
        # 匹配用例开始行: testcases/test_xxx.py::TestXxx::test_data_driven[CASE_ID]
        case_match = re.search(r"test_data_driven\[(.+?)\]", line)
        if case_match:
            current_case_id = case_match.group(1)

        # 匹配 test_response_time 开始行
        if "test_response_time" in line and "::test_response_time" in line:
            current_case_id = "__response_time__"

        # 匹配结果状态（可能在同一行末尾，也可能单独一行）
        status_match = re.search(r"(PASSED|FAILED|ERROR|SKIPPED)\s+\[?\s*\d*%?\s*\]?", line)
        if status_match and current_case_id:
            results[current_case_id] = status_match.group(1)
            current_case_id = None

    return results


def _parse_response_details_from_log(log_dir: Path) -> Dict[str, Dict[str, str]]:
    """
    从最新日志文件中解析每个用例的响应详情。
    返回 {case_id: {"http_status": "200", "biz_code": "0", "message": "请求成功"}}
    """
    log_files = sorted(log_dir.glob("test_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not log_files:
        return {}

    latest_log = log_files[0]
    content = latest_log.read_text(encoding="utf-8")
    lines = content.splitlines()

    details = {}
    current_case_id = None
    current_http_status = None
    collecting_response_body = False
    response_body_lines = []

    for line in lines:
        # 匹配用例开始: 执行用例: [CASE_ID] 标题
        case_match = re.search(r"执行用例: \[(.+?)\]", line)
        if case_match:
            # 保存上一个用例的数据
            if current_case_id and current_case_id not in details:
                _save_case_detail(details, current_case_id, current_http_status, response_body_lines)
            current_case_id = case_match.group(1)
            current_http_status = None
            collecting_response_body = False
            response_body_lines = []
            continue

        # 匹配响应状态码
        status_match = re.search(r"响应状态码: (\d+)", line)
        if status_match and current_case_id:
            current_http_status = status_match.group(1)
            continue

        # 匹配响应体开始
        body_match = re.search(r"响应体: (.+)", line)
        if body_match and current_case_id:
            response_body_lines = [body_match.group(1)]
            # 检查是否是单行 JSON
            try:
                json.loads(body_match.group(1))
                collecting_response_body = False
            except (json.JSONDecodeError, ValueError):
                collecting_response_body = True
            continue

        # 继续收集多行响应体
        if collecting_response_body and current_case_id:
            if re.match(r"^\d{4}-\d{2}-\d{2}", line):
                # 新的日志行开始，停止收集
                collecting_response_body = False
                _save_case_detail(details, current_case_id, current_http_status, response_body_lines)
            else:
                response_body_lines.append(line)

    # 处理最后一个用例
    if current_case_id and current_case_id not in details:
        _save_case_detail(details, current_case_id, current_http_status, response_body_lines)

    return details


def _save_case_detail(details: dict, case_id: str, http_status: Optional[str], body_lines: List[str]):
    """解析响应体并保存用例详情"""
    biz_code = "-"
    message = "-"

    if body_lines:
        body_text = "\n".join(body_lines).strip()
        try:
            body_json = json.loads(body_text)
            if "code" in body_json:
                biz_code = str(body_json["code"])
            if "message" in body_json:
                message = str(body_json["message"])
        except (json.JSONDecodeError, ValueError):
            pass

    details[case_id] = {
        "http_status": http_status or "-",
        "biz_code": biz_code,
        "message": message,
        "response_body": body_text if body_lines else "-",
    }


def _truncate(text: str, max_len: int = 0) -> str:
    """截断过长的文本，max_len<=0 时不截断"""
    if text is None:
        return ""
    text = str(text)
    if max_len <= 0:
        return text
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def build_result_table(api_name: str, cases: List[Dict], test_results: Dict[str, str],
                       response_details: Optional[Dict[str, Dict[str, str]]] = None) -> str:
    """
    构建测试结果表格文本并返回。
    同时打印到控制台。
    """
    # 表头字段
    columns = ["接口名称", "用例标题", "请求数据", "HTTP状态码", "业务code", "响应消息", "执行结果", "返回体"]

    # 构建表格数据行
    rows = []
    for case in cases:
        case_id = case["case_id"]
        title = case["title"]
        body = case.get("body")
        if body and isinstance(body, dict) and body:
            body_str = json.dumps(body, ensure_ascii=False)
        else:
            body_str = "-"
        result_status = test_results.get(case_id, "UNKNOWN")
        if result_status == "PASSED":
            result_display = "通过"
        elif result_status == "FAILED":
            result_display = "失败"
        elif result_status == "ERROR":
            result_display = "错误"
        elif result_status == "SKIPPED":
            result_display = "跳过"
        else:
            result_display = "未知"

        # 获取响应详情
        detail = (response_details or {}).get(case_id, {})
        http_status = detail.get("http_status", "-")
        biz_code = detail.get("biz_code", "-")
        message = detail.get("message", "-") or "-"
        response_body = detail.get("response_body", "-") or "-"
        # 将返回体压缩为单行以适配表格
        response_body = response_body.replace("\n", "").replace("\r", "")

        rows.append([api_name, title, body_str, http_status, biz_code, message, result_display, response_body])

    # 添加响应时间测试行
    rt_status = test_results.get("__response_time__", "UNKNOWN")
    if rt_status == "PASSED":
        rt_display = "通过"
    elif rt_status == "FAILED":
        rt_display = "失败"
    else:
        rt_display = "未知"
    rows.append([api_name, "响应时间检测(≤5s)", "-", "-", "-", "-", rt_display, "-"])

    # 计算每列宽度（考虑中文字符显示宽度）
    def display_width(s: str) -> int:
        width = 0
        for ch in s:
            if '\u4e00' <= ch <= '\u9fff' or '\uff00' <= ch <= '\uffef' or '\u3000' <= ch <= '\u303f':
                width += 2
            else:
                width += 1
        return width

    def pad_str(s: str, target_width: int) -> str:
        current_width = display_width(s)
        padding = target_width - current_width
        return s + " " * max(0, padding)

    # 计算每列最大宽度
    all_data = [columns] + rows
    widths = [0] * len(columns)
    for row in all_data:
        for i, cell in enumerate(row):
            w = display_width(cell)
            if w > widths[i]:
                widths[i] = w

    # 构建表格文本
    lines = []
    header_line = "|".join(pad_str(columns[i], widths[i]) for i in range(len(columns)))
    separator = "+".join("-" * widths[i] for i in range(len(columns)))

    lines.append("")
    lines.append("📊 测试执行结果")
    lines.append(header_line)
    lines.append(separator)

    # 数据行
    for row in rows:
        line = "|".join(pad_str(row[i], widths[i]) for i in range(len(columns)))
        lines.append(line)

    # 统计
    passed = sum(1 for r in rows if r[6] == "通过")
    failed = sum(1 for r in rows if r[6] == "失败")
    total = len(rows)
    lines.append("")
    lines.append(f"📈 汇总: 共 {total} 条用例, 通过 {passed}, 失败 {failed}")

    table_text = "\n".join(lines)

    # 打印到控制台
    print(table_text)

    return table_text


def _rejoin_args(args_list: List[str]) -> str:
    """
    将 shell 拆散的参数列表重新拼成一条完整的命令字符串。
    对含空格或特殊字符的参数用单引号包裹，确保后续 shlex.split 能正确解析。
    """
    parts = []
    for arg in args_list:
        if " " in arg or ";" in arg or "'" in arg or '"' in arg or "=" in arg:
            # 用单引号包裹，内部的单引号用 '\'' 转义
            escaped = arg.replace("'", "'\\''")
            parts.append(f"'{escaped}'")
        else:
            parts.append(arg)
    return " ".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="cURL 一键生成接口自动化测试用例并执行",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python curl_to_test.py "curl --location 'https://api.example.com/v1/users' --header 'Content-Type: application/json' --data '{\"name\": \"test\"}'"

    # 从 stdin 读取 curl 命令（适合粘贴多行 curl）
    python curl_to_test.py --stdin

    # 仅生成用例不执行
    python curl_to_test.py --no-run "curl ..."

    # 指定用例名称
    python curl_to_test.py --name my_api "curl ..."
        """,
    )
    parser.add_argument("curl", nargs="?", default=None, help="完整的 curl 命令字符串")
    parser.add_argument("--stdin", action="store_true", help="从标准输入读取 curl 命令（支持多行粘贴）")
    parser.add_argument("--no-run", action="store_true", help="仅生成用例，不执行测试")
    parser.add_argument("--name", help="自定义接口名称（用于文件命名）")

    args, unknown_args = parser.parse_known_args()

    # 支持从 stdin 读取或从剩余命令行参数拼接
    if args.stdin or (args.curl is None and not sys.stdin.isatty()):
        print("📎 从标准输入读取 curl 命令 (粘贴后按 Ctrl+D 结束)...")
        curl_input = sys.stdin.read().strip()
    elif args.curl is not None:
        # 显式传了 curl 参数（用引号包裹的整条命令）
        # 同时把 unknown_args 也拼上，以防有部分内容泄漏到 unknown 中
        if unknown_args:
            curl_input = args.curl + " " + _rejoin_args(unknown_args)
        else:
            curl_input = args.curl
    elif unknown_args:
        # 没有传 curl 位置参数，但 shell 把 curl 命令拆成了多个参数
        # 比如: python curl_to_test.py curl --location 'url' --header 'xxx'
        curl_input = _rejoin_args(unknown_args)
    else:
        parser.error("请提供 curl 命令字符串，或使用 --stdin 从标准输入读取")
        return

    # 修复: 如果 shell 把 --data 后的 JSON body 中的特殊字符（如 [] {}）分割丢失，
    # 尝试从原始 sys.argv 中重新拼接完整的 curl 命令
    if "--data" not in curl_input and "--data-raw" not in curl_input:
        raw_argv = " ".join(sys.argv[1:])
        if "--data" in raw_argv or "--data-raw" in raw_argv:
            curl_input = raw_argv

    # 额外修复: 检查解析后是否有 body，如果没有但原始输入包含 --data，
    # 尝试用正则直接提取 --data 后面的 JSON
    _preliminary = parse_curl(curl_input)
    if _preliminary["body"] is None and ("--data" in curl_input or "--data-raw" in curl_input):
        # 尝试从原始 curl 命令中用正则提取 JSON body
        data_match = re.search(
            r"--data(?:-raw|-binary)?\s+['\"]?(\{.*?\})['\"]?(?:\s+--|$)",
            curl_input,
            re.DOTALL,
        )
        if data_match:
            try:
                extracted_body = json.loads(data_match.group(1))
                _preliminary["body"] = extracted_body
                if _preliminary["method"] == "GET":
                    _preliminary["method"] = "POST"
            except (json.JSONDecodeError, TypeError):
                pass

    print(f"\n{'=' * 60}")
    print("🚀 cURL → 接口自动化测试用例生成器")
    print(f"{'=' * 60}\n")

    # Step 1: 解析 curl
    print("📋 Step 1: 解析 curl 命令...")
    parsed = _preliminary if _preliminary["body"] is not None else parse_curl(curl_input)
    print(f"   方法: {parsed['method']}")
    print(f"   URL: {parsed['url']}")
    print(f"   请求头: {len(parsed['headers'])} 个")
    print(f"   Cookie: {len(parsed['cookies'])} 个")
    print(f"   请求体: {'有' if parsed['body'] else '无'}")

    # Step 2: 提取接口信息
    api_info = extract_api_info(parsed)
    if args.name:
        api_info["api_name"] = args.name

    print(f"\n📌 接口名称: {api_info['api_name']}")
    print(f"   接口路径: {api_info['api_path']}")

    # Step 3: 生成测试用例
    print("\n📝 Step 2: 生成测试用例...")
    cases = generate_test_cases(parsed, api_info)
    print(f"   生成了 {len(cases)} 个测试用例")

    # Step 4: 生成 YAML 数据文件
    yaml_file_name = f"{api_info['api_name']}.yaml"
    yaml_path = generate_yaml_file(cases, api_info)
    print(f"   数据文件: {yaml_path}")

    # Step 5: 生成测试代码文件
    test_path = generate_test_file(api_info, yaml_file_name)
    print(f"   测试文件: {test_path}")

    # Step 6: 执行测试
    if not args.no_run:
        print(f"\n▶️  Step 3: 执行测试...")
        returncode, report_path, pytest_output = run_tests(test_path)

        # 解析测试结果并输出表格
        test_results = _parse_pytest_results(pytest_output)
        response_details = _parse_response_details_from_log(BASE_DIR / "logs")
        table_text = build_result_table(api_info["api_name"], cases, test_results, response_details)

        # 将结果表格追加到报告文件
        with open(report_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 60}\n")
            f.write(table_text)
            f.write("\n")

        # 将结果表格追加到日志文件（查找最新的日志文件）
        log_dir = BASE_DIR / "logs"
        log_files = sorted(log_dir.glob("test_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if log_files:
            latest_log = log_files[0]
            with open(latest_log, "a", encoding="utf-8") as f:
                f.write(f"\n{'=' * 60}\n")
                f.write(table_text)
                f.write("\n")

        print(f"\n📁 测试报告: {report_path}")

        if returncode == 0:
            print(f"✅ 全部测试通过!")
        else:
            print(f"⚠️  部分测试未通过 (退出码: {returncode})")
    else:
        print(f"\n⏭️  已跳过测试执行 (--no-run)")

    print(f"\n{'=' * 60}")
    print("📁 生成文件汇总:")
    print(f"   测试数据: testdata/{yaml_file_name}")
    print(f"   测试用例: testcases/test_{api_info['api_name']}.py")
    if not args.no_run:
        print(f"   测试报告: {report_path}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
