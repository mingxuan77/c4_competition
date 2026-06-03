"""ToolRegistry — 工具注册中心单例，支持装饰器注册和动态调用"""

import functools
from typing import Callable, Any
from workers.tools.schema import ToolResult


class ToolRegistry:
    """全局工具注册中心（单例模式）。

    使用方式:
      # 方式1: 装饰器
      @tool(name="my_tool", description="...")
      def my_tool(data): ...

      # 方式2: 直接注册
      ToolRegistry.register("my_tool", my_func, description="...")

      # 调用
      result = ToolRegistry.call("my_tool", data="hello")
    """

    _instance: "ToolRegistry | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
            cls._instance._schemas = {}
        return cls._instance

    def register(
        self,
        name: str,
        func: Callable,
        description: str = "",
        parameters: dict[str, str] | None = None,
    ):
        """注册一个工具。

        Args:
            name: 工具唯一名称（如 "export_excel"）
            func: 工具调用函数
            description: 工具功能描述（LLM 用来决定何时调用）
            parameters: 参数说明 {param_name: description}
        """
        self._tools[name] = func
        self._schemas[name] = {
            "name": name,
            "description": description,
            "parameters": parameters or {},
        }

    def get(self, name: str) -> Callable | None:
        """获取已注册的工具函数。"""
        return self._tools.get(name)

    def get_schema(self, name: str) -> dict | None:
        """获取工具的 schema 描述。"""
        return self._schemas.get(name)

    def list_tools(self) -> list[dict]:
        """列出所有已注册工具及其 schema。"""
        return [
            {"name": name, **schema}
            for name, schema in self._schemas.items()
        ]

    def get_tools_prompt(self) -> str:
        """生成可供 LLM 使用的工具列表描述文本。"""
        if not self._tools:
            return "（无可用工具）"
        lines = []
        for name, schema in self._schemas.items():
            params_desc = ", ".join(
                f"{p}: {d}" for p, d in schema.get("parameters", {}).items()
            )
            lines.append(f"- **{name}**: {schema['description']}")
            if params_desc:
                lines.append(f"  参数: {params_desc}")
        return "\n".join(lines)

    def call(self, name: str, **kwargs) -> ToolResult:
        """调用已注册的工具。

        Args:
            name: 工具名称
            **kwargs: 传递给工具函数的参数

        Returns:
            ToolResult(success, data, error, files, metadata)
        """
        func = self._tools.get(name)
        if not func:
            return ToolResult(
                success=False,
                error=f"工具 '{name}' 未注册。可用工具: {list(self._tools.keys())}",
            )
        try:
            result = func(**kwargs)
            if isinstance(result, ToolResult):
                return result
            # 如果函数返回的不是 ToolResult，自动包装
            return ToolResult(success=True, data=result)
        except TypeError as e:
            return ToolResult(
                success=False,
                error=f"参数错误: {e}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"工具执行异常: {type(e).__name__}: {e}",
            )


# ─── 装饰器 ─────────────────────────────────────

def tool(
    name: str,
    description: str = "",
    parameters: dict[str, str] | None = None,
):
    """装饰器：将函数注册为工具。

    Usage:
        @tool(name="export_excel", description="导出Excel",
              parameters={"data": "数据", "filename": "文件名"})
        def export_excel(data, filename): ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # 注册到全局 ToolRegistry
        ToolRegistry().register(
            name=name,
            func=func,
            description=description,
            parameters=parameters,
        )
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════
# YAML 配置加载
# ═══════════════════════════════════════════════════

def load_tools_from_yaml(yaml_path: str | None = None):
    """从 YAML 配置文件加载外部工具。

    在系统启动时调用一次，注册配置文件中声明的工具。
    """
    import os

    if yaml_path is None:
        yaml_path = os.path.join(os.path.dirname(__file__), "tools.yaml")

    if not os.path.exists(yaml_path):
        return []

    try:
        import yaml
    except ImportError:
        return []

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except Exception:
        return []

    tools = config.get("tools", []) if config else []
    registered = []

    if not tools:
        return registered

    for t in tools:
        name = t.get("name", "")
        desc = t.get("description", "")
        tool_type = t.get("type", "")

        if tool_type == "http":
            endpoint = t.get("endpoint", "")
            method = t.get("method", "GET")
            headers = t.get("headers", {})

            def make_http_tool(endpoint=endpoint, method=method, headers=headers):
                def http_tool(**kwargs):
                    from workers.tools.builtin.http_client import http_request
                    return http_request(
                        url=endpoint,
                        method=method,
                        headers=headers,
                        body=kwargs.get("body"),
                        timeout=kwargs.get("timeout", 15),
                    )
                return http_tool

            ToolRegistry().register(
                name=name,
                func=make_http_tool(),
                description=desc,
                parameters=t.get("parameters", {}),
            )
            registered.append(name)

        elif tool_type == "script":
            command = t.get("command", "")

            def make_script_tool(command=command):
                import subprocess
                def script_tool(**kwargs):
                    try:
                        proc = subprocess.run(
                            command.split(),
                            capture_output=True,
                            text=True,
                            timeout=kwargs.get("timeout", 30),
                        )
                        from workers.tools.schema import ToolResult
                        return ToolResult(
                            success=proc.returncode == 0,
                            data={"stdout": proc.stdout[:5000], "stderr": proc.stderr[:5000]},
                        )
                    except Exception as e:
                        from workers.tools.schema import ToolResult
                        return ToolResult(success=False, error=str(e))
                return script_tool

            ToolRegistry().register(
                name=name,
                func=make_script_tool(),
                description=desc,
                parameters=t.get("parameters", {}),
            )
            registered.append(name)

    return registered
