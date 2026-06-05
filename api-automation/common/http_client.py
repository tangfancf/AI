"""
HTTP 客户端封装 - 统一管理请求发送、日志记录、异常处理
"""
import json
import logging
from typing import Any, Optional

import requests

from config.settings import get_base_url, get_timeout

logger = logging.getLogger(__name__)


class HttpClient:
    """可复用的 HTTP 客户端"""

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        self.base_url = base_url or get_base_url()
        self.timeout = timeout or get_timeout()
        self.session = requests.Session()
        self._token: Optional[str] = None

    @property
    def token(self) -> Optional[str]:
        return self._token

    @token.setter
    def token(self, value: str):
        self._token = value
        self.session.headers.update({"Authorization": f"Bearer {value}"})

    def set_headers(self, headers: dict):
        """设置自定义请求头"""
        self.session.headers.update(headers)

    def request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        data: Optional[Any] = None,
        headers: Optional[dict] = None,
        files: Optional[dict] = None,
        **kwargs,
    ) -> requests.Response:
        """
        发送 HTTP 请求

        Args:
            method: 请求方法 (GET, POST, PUT, DELETE, PATCH)
            path: 接口路径 (相对路径或绝对 URL)
            params: URL 查询参数
            json_data: JSON 请求体
            data: 表单数据
            headers: 额外请求头
            files: 上传文件
            **kwargs: 其他 requests 参数

        Returns:
            requests.Response 对象
        """
        url = path if path.startswith("http") else f"{self.base_url}{path}"

        logger.info(f"{'=' * 60}")
        logger.info(f"请求方法: {method.upper()}")
        logger.info(f"请求URL: {url}")
        if params:
            logger.info(f"查询参数: {json.dumps(params, ensure_ascii=False)}")
        if json_data:
            logger.info(f"请求体: {json.dumps(json_data, ensure_ascii=False)}")

        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json_data,
                data=data,
                headers=headers,
                files=files,
                timeout=self.timeout,
                **kwargs,
            )

            logger.info(f"响应状态码: {response.status_code}")
            try:
                logger.info(
                    f"响应体: {json.dumps(response.json(), ensure_ascii=False, indent=2)}"
                )
            except (json.JSONDecodeError, ValueError):
                logger.info(f"响应体(文本): {response.text[:500]}")
            logger.info(f"{'=' * 60}")

            return response

        except requests.exceptions.Timeout:
            logger.error(f"请求超时: {url}")
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"连接失败: {url}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e}")
            raise

    def get(self, path: str, params: Optional[dict] = None, **kwargs) -> requests.Response:
        return self.request("GET", path, params=params, **kwargs)

    def post(
        self, path: str, json_data: Optional[dict] = None, **kwargs
    ) -> requests.Response:
        return self.request("POST", path, json_data=json_data, **kwargs)

    def put(
        self, path: str, json_data: Optional[dict] = None, **kwargs
    ) -> requests.Response:
        return self.request("PUT", path, json_data=json_data, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.request("DELETE", path, **kwargs)

    def patch(
        self, path: str, json_data: Optional[dict] = None, **kwargs
    ) -> requests.Response:
        return self.request("PATCH", path, json_data=json_data, **kwargs)
