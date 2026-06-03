"""工具注册中心 — 统一的工具注册、发现、调用机制"""

from workers.tools.registry import ToolRegistry, tool
from workers.tools.schema import ToolParam, ToolResult

__all__ = ["ToolRegistry", "tool", "ToolParam", "ToolResult"]

# 自动加载 tools.yaml 中配置的外部工具
from workers.tools.registry import load_tools_from_yaml
load_tools_from_yaml()
