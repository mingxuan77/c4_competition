"""HTTP Worker — 调用外部 API / Webhook"""

from workers.base_worker import BaseWorker


class HTTPWorker(BaseWorker):
    """HTTP 请求执行器——调用外部 REST API、触发 Webhook、抓取数据。"""

    def __init__(self):
        super().__init__("HTTPWorker")

    def execute(self, task: dict) -> dict:
        desc = task.get("description", "")
        params = task.get("params", {})
        result = {"worker": self.name}

        url = params.get("url", "")
        method = params.get("method", "GET")
        headers = params.get("headers", None)
        body = params.get("body", None)

        if not url:
            result["output"] = f"[HTTP请求] 未提供URL，跳过执行"
            return result

        http_result = self._call_tool(
            "http_request",
            url=url,
            method=method,
            headers=headers,
            body=body,
            timeout=params.get("timeout", 15),
        )

        meta = http_result.get("metadata", {})
        if http_result.get("success"):
            data = http_result.get("data", {})
            result["output"] = (
                f"[HTTP请求] ✅ {method} {url}\n"
                f"状态码: {data.get('status_code')} "
                f"| 耗时: {meta.get('elapsed_ms', 0)}ms\n"
                f"响应: {str(data.get('body', ''))[:300]}"
            )
        else:
            result["output"] = (
                f"[HTTP请求] ❌ {method} {url}\n"
                f"错误: {http_result.get('error', '未知错误')}"
            )

        result["http_result"] = http_result
        return result
