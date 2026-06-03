"""HTTP 客户端工具 — 调用外部 REST API、Webhook"""

import time
from workers.tools.registry import tool
from workers.tools.schema import ToolResult


@tool(
    name="http_request",
    description="发送HTTP请求到外部API，支持GET/POST/PUT/DELETE，返回响应数据",
    parameters={
        "url": "请求URL",
        "method": "HTTP方法: GET/POST/PUT/DELETE（默认GET）",
        "headers": "请求头 dict（可选）",
        "body": "请求体字符串（可选，用于POST/PUT）",
        "timeout": "超时秒数（默认15）",
    },
)
def http_request(
    url: str = "",
    method: str = "GET",
    headers: dict | None = None,
    body: str | None = None,
    timeout: int = 15,
) -> ToolResult:
    try:
        import requests
    except ImportError:
        return ToolResult(success=False, error="请安装 requests: pip install requests")

    if not url:
        return ToolResult(success=False, error="URL 不能为空")

    method = method.upper()
    if method not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
        return ToolResult(success=False, error=f"不支持的HTTP方法: {method}")

    try:
        start = time.time()
        kwargs = {"timeout": timeout}
        if headers:
            kwargs["headers"] = headers
        if body and method in ("POST", "PUT", "PATCH"):
            kwargs["data"] = body

        resp = requests.request(method, url, **kwargs)
        elapsed_ms = round((time.time() - start) * 1000)

        # 解析响应
        response_body = None
        content_type = resp.headers.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                response_body = resp.json()
            except Exception:
                response_body = resp.text[:5000]
        else:
            response_body = resp.text[:5000]

        success = 200 <= resp.status_code < 300
        return ToolResult(
            success=success,
            data={
                "status_code": resp.status_code,
                "body": response_body,
            },
            metadata={
                "elapsed_ms": elapsed_ms,
                "url": url,
                "method": method,
                "content_type": content_type,
            },
            error=None if success else f"HTTP {resp.status_code}: {resp.reason}",
        )
    except Exception as e:
        return ToolResult(success=False, error=f"HTTP请求失败: {e}")
