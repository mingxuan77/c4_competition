"""工具参数与结果数据结构"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolParam:
    """工具参数定义"""
    name: str
    description: str
    type: str = "string"  # string, number, boolean, object, array
    required: bool = True
    default: Any = None


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any = None           # 工具返回的数据
    error: str | None = None   # 错误信息
    files: list[str] = field(default_factory=list)  # 生成的文件路径列表
    metadata: dict = field(default_factory=dict)     # 额外元信息（文件大小、耗时等）

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "files": self.files,
            "metadata": self.metadata,
        }
