# 真实工具执行能力 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给多智能体系统添加真正的工具调用能力——文件导出(Word/Excel/PDF)、Python沙箱执行、HTTP API调用——让Worker从"Prompt编辑器"变成能完成端到端任务的工具使用者。

**Architecture:** 在现有 LangGraph → Worker 架构上新增 ToolRegistry 层。ToolRegistry 提供统一的工具注册/发现/调用机制，支持 @tool 装饰器和 YAML 配置两种注册方式。Worker 通过 ToolRegistry 获取工具并真正执行，返回实际产物（文件路径、执行结果、API响应）而非模拟文本。

**Tech Stack:** Python, python-docx, openpyxl, fpdf2, requests, PyYAML, subprocess, Streamlit

---

## File Structure

```
workers/tools/                    ← 新建
├── __init__.py
├── registry.py                   # ToolRegistry 单例 + @tool 装饰器
├── schema.py                     # ToolParam, ToolResult 数据结构
├── builtin/
│   ├── __init__.py
│   ├── file_export.py            # export_docx, export_excel, export_pdf
│   ├── sandbox.py                # run_python 沙箱
│   └── http_client.py            # http_request
├── tools.yaml                    # 外部工具配置文件

workers/
├── base_worker.py                ← 修改: 添加 _call_tool() 方法
├── report_exporter.py            ← 重写: 接入 ToolRegistry，真正写文件
├── code_executor.py              ← 修改: 接入 run_python 沙箱
├── http_worker.py                ← 新建

meta_agent/
├── langgraph_engine.py           ← 修改: 注册 HTTPWorker

app.py                            ← 修改: 右侧面板追加下载区域
requirements.txt                  ← 修改: 添加新依赖
```

---

### Task 1: 创建 ToolRegistry 数据模型 (schema.py)

**Files:**
- Create: `workers/tools/__init__.py`
- Create: `workers/tools/schema.py`

- [ ] **Step 1: Create `workers/tools/__init__.py`**

```python
"""工具注册中心 — 统一的工具注册、发现、调用机制"""

from workers.tools.registry import ToolRegistry, tool
from workers.tools.schema import ToolParam, ToolResult

__all__ = ["ToolRegistry", "tool", "ToolParam", "ToolResult"]
```

- [ ] **Step 2: Create `workers/tools/schema.py`**

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add workers/tools/__init__.py workers/tools/schema.py
git commit -m "feat: add ToolRegistry data models (ToolParam, ToolResult)"
```

---

### Task 2: 实现 ToolRegistry 核心 (registry.py)

**Files:**
- Create: `workers/tools/registry.py`

- [ ] **Step 1: Create `workers/tools/registry.py`**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add workers/tools/registry.py
git commit -m "feat: implement ToolRegistry core with decorator support"
```

---

### Task 3: 实现文件导出工具 (file_export.py)

**Files:**
- Create: `workers/tools/builtin/__init__.py`
- Create: `workers/tools/builtin/file_export.py`

- [ ] **Step 1: Create `workers/tools/builtin/__init__.py`**

```python
"""内置工具集 — 系统预置的高频工具"""
```

- [ ] **Step 2: Create `workers/tools/builtin/file_export.py`**

```python
"""文件导出工具: Word(.docx), Excel(.xlsx), PDF(.pdf)"""

import os
import time
from datetime import datetime
from workers.tools.registry import tool
from workers.tools.schema import ToolResult

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "outputs")


def _ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return OUTPUT_DIR


# ═══════════════════════════════════════════
# Word 导出
# ═══════════════════════════════════════════

@tool(
    name="export_docx",
    description="将Markdown文本和表格数据导出为Word(.docx)文件，支持标题层级、表格、页眉页脚",
    parameters={
        "title": "报告标题",
        "content": "Markdown格式的正文内容",
        "table_data": "可选，list[dict]格式的表格数据",
    },
)
def export_docx(
    title: str = "分析报告",
    content: str = "",
    table_data: list[dict] | None = None,
) -> ToolResult:
    try:
        from docx import Document
        from docx.shared import Inches, Pt, Cm, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        return ToolResult(success=False, error="请安装 python-docx: pip install python-docx")

    try:
        doc = Document()

        # 页眉
        section = doc.sections[0]
        header = section.header
        p = header.paragraphs[0]
        p.text = f"多智能体协同分析报告 | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        for run in p.runs:
            run.font.size = Pt(8)
            run.font.color.rgb = RGBColor(128, 128, 128)

        # 标题
        doc.add_heading(title, level=0)

        # 正文（按段落处理）
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("## "):
                doc.add_heading(line[3:], level=2)
            elif line.startswith("### "):
                doc.add_heading(line[4:], level=3)
            elif line.startswith("- "):
                doc.add_paragraph(line[2:], style="List Bullet")
            else:
                doc.add_paragraph(line)

        # 表格
        if table_data and len(table_data) > 0:
            doc.add_heading("数据汇总", level=2)
            headers = list(table_data[0].keys())
            table = doc.add_table(rows=1, cols=len(headers), style="Light Grid Accent 1")
            # 表头
            for i, h in enumerate(headers):
                cell = table.rows[0].cells[i]
                cell.text = str(h)
                for run in cell.paragraphs[0].runs:
                    run.font.bold = True
            # 数据行
            for row_data in table_data:
                row = table.add_row()
                for i, h in enumerate(headers):
                    row.cells[i].text = str(row_data.get(h, ""))

        # 页脚
        footer = section.footer
        p = footer.paragraphs[0]
        p.text = "由 Meta-Agent 多智能体协同调度系统自动生成"
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.font.size = Pt(8)
            run.font.color.rgb = RGBColor(128, 128, 128)

        # 保存
        out_dir = _ensure_output_dir()
        safe_title = "".join(c for c in title if c.isalnum() or c in " _-")[:40]
        filename = f"{safe_title}_{int(time.time())}.docx"
        filepath = os.path.join(out_dir, filename)
        doc.save(filepath)

        file_size = os.path.getsize(filepath)
        return ToolResult(
            success=True,
            data=f"Word报告已生成: {filename}",
            files=[filepath],
            metadata={"filename": filename, "size_kb": round(file_size / 1024, 1)},
        )
    except Exception as e:
        return ToolResult(success=False, error=f"Word导出失败: {e}")


# ═══════════════════════════════════════════
# Excel 导出
# ═══════════════════════════════════════════

@tool(
    name="export_excel",
    description="将数据导出为Excel(.xlsx)文件，支持多Sheet、自动列宽、条件格式",
    parameters={
        "filename": "文件名（不含扩展名）",
        "sheets": "dict，key=Sheet名称，value=list[dict]数据",
    },
)
def export_excel(
    filename: str = "data_export",
    sheets: dict[str, list[dict]] | None = None,
) -> ToolResult:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        return ToolResult(success=False, error="请安装 openpyxl: pip install openpyxl")

    try:
        wb = Workbook()
        # 删除默认Sheet
        wb.remove(wb.active)

        sheets = sheets or {"Sheet1": []}
        for sheet_name, data in sheets.items():
            ws = wb.create_sheet(title=sheet_name[:31])  # Excel Sheet名最长31字符

            if not data:
                ws.cell(row=1, column=1, value="（无数据）")
                continue

            headers = list(data[0].keys())

            # 表头样式
            header_font = Font(name="Microsoft YaHei", bold=True, color="FFFFFF", size=11)
            header_fill = PatternFill(start_color="4A90D9", end_color="4A90D9", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")
            thin_border = Border(
                left=Side(style="thin"), right=Side(style="thin"),
                top=Side(style="thin"), bottom=Side(style="thin"),
            )

            # 写入表头
            for col_idx, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_idx, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = thin_border

            # 写入数据
            for row_idx, row_data in enumerate(data, 2):
                for col_idx, header in enumerate(headers, 1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=row_data.get(header, ""))
                    cell.border = thin_border
                    cell.alignment = Alignment(vertical="center")

            # 自动列宽
            for col_idx in range(1, len(headers) + 1):
                max_width = len(str(headers[col_idx - 1])) * 2
                for row_idx in range(2, len(data) + 2):
                    val = ws.cell(row=row_idx, column=col_idx).value
                    if val:
                        max_width = max(max_width, len(str(val)) * 1.5)
                ws.column_dimensions[get_column_letter(col_idx)].width = min(max_width + 2, 50)

            # 冻结首行
            ws.freeze_panes = "A2"

        # 保存
        out_dir = _ensure_output_dir()
        safe_name = "".join(c for c in filename if c.isalnum() or c in " _-")[:40]
        filepath = os.path.join(out_dir, f"{safe_name}_{int(time.time())}.xlsx")
        wb.save(filepath)

        file_size = os.path.getsize(filepath)
        return ToolResult(
            success=True,
            data=f"Excel文件已生成: {os.path.basename(filepath)}（{len(sheets)} 个Sheet）",
            files=[filepath],
            metadata={"filename": os.path.basename(filepath), "size_kb": round(file_size / 1024, 1),
                      "sheets": list(sheets.keys())},
        )
    except Exception as e:
        return ToolResult(success=False, error=f"Excel导出失败: {e}")


# ═══════════════════════════════════════════
# PDF 导出
# ═══════════════════════════════════════════

@tool(
    name="export_pdf",
    description="将Markdown/HTML内容导出为PDF文件，支持分页、页眉页脚",
    parameters={
        "title": "报告标题",
        "content": "Markdown格式的正文内容",
    },
)
def export_pdf(
    title: str = "分析报告",
    content: str = "",
) -> ToolResult:
    try:
        from fpdf import FPDF
    except ImportError:
        return ToolResult(success=False, error="请安装 fpdf2: pip install fpdf2")

    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)

        # 注册中文字体（尝试多个路径）
        font_loaded = False
        font_paths = [
            "C:/Windows/Fonts/msyh.ttc",       # 微软雅黑
            "C:/Windows/Fonts/simsun.ttc",      # 宋体
            "C:/Windows/Fonts/simhei.ttf",      # 黑体
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/System/Library/Fonts/PingFang.ttc",
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                pdf.add_font("CJK", "", fp, uni=True)
                pdf.add_font("CJK", "B", fp, uni=True)
                font_loaded = True
                break

        if not font_loaded:
            return ToolResult(
                success=False,
                error="未找到中文字体。请确保系统安装了微软雅黑或宋体字体。"
            )

        # 首页
        pdf.add_page()
        pdf.set_font("CJK", "B", 20)
        pdf.cell(0, 15, title, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(8)
        pdf.set_font("CJK", "", 9)
        pdf.cell(0, 8, f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.cell(0, 8, "由 Meta-Agent 多智能体协同调度系统自动生成", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(10)

        # 正文
        pdf.set_font("CJK", "", 11)
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                pdf.ln(4)
                continue
            if line.startswith("## "):
                pdf.set_font("CJK", "B", 14)
                pdf.cell(0, 10, line[3:], new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("CJK", "", 11)
                pdf.ln(2)
            elif line.startswith("### "):
                pdf.set_font("CJK", "B", 12)
                pdf.cell(0, 8, line[4:], new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("CJK", "", 11)
                pdf.ln(2)
            elif line.startswith("- "):
                pdf.cell(8, 8, "•")
                pdf.multi_cell(0, 8, line[2:])
            else:
                pdf.multi_cell(0, 8, line)

        # 保存
        out_dir = _ensure_output_dir()
        safe_title = "".join(c for c in title if c.isalnum() or c in " _-")[:40]
        filepath = os.path.join(out_dir, f"{safe_title}_{int(time.time())}.pdf")
        pdf.output(filepath)

        file_size = os.path.getsize(filepath)
        return ToolResult(
            success=True,
            data=f"PDF报告已生成: {os.path.basename(filepath)}",
            files=[filepath],
            metadata={
                "filename": os.path.basename(filepath),
                "size_kb": round(file_size / 1024, 1),
                "pages": pdf.pages_count,
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=f"PDF导出失败: {e}")
```

- [ ] **Step 3: Commit**

```bash
git add workers/tools/builtin/__init__.py workers/tools/builtin/file_export.py
git commit -m "feat: add file export tools (docx, xlsx, pdf)"
```

---

### Task 4: 实现 Python 沙箱工具 (sandbox.py)

**Files:**
- Create: `workers/tools/builtin/sandbox.py`

- [ ] **Step 1: Create `workers/tools/builtin/sandbox.py`**

```python
"""Python 沙箱执行工具 — 安全隔离运行用户代码"""

import os
import subprocess
import tempfile
import time
from workers.tools.registry import tool
from workers.tools.schema import ToolResult

# 禁止的模块列表
BLOCKED_MODULES = [
    "os", "subprocess", "shutil", "sys", "ctypes", "socket",
    "pickle", "marshal", "importlib", "builtins",
]

SANDBOX_TIMEOUT = 10  # 秒
MAX_OUTPUT_BYTES = 50 * 1024  # 50KB


@tool(
    name="run_python",
    description="在安全沙箱中执行Python代码，返回stdout/stderr。禁止文件系统和网络操作。",
    parameters={
        "code": "Python源代码字符串",
        "timeout": "超时秒数（默认10）",
    },
)
def run_python(code: str = "", timeout: int = SANDBOX_TIMEOUT) -> ToolResult:
    if not code or not code.strip():
        return ToolResult(success=False, error="代码为空")

    # 在代码前注入安全检查
    guard = "\n".join(
        f"__import__('builtins').__dict__['{m}'] = type('Blocked', (), {{'__getattr__': lambda *a: exec('raise ImportError(\\\"{m} is blocked\\\")')}})()"
        for m in BLOCKED_MODULES
    )
    full_code = f"""
# === 沙箱安全守卫 ===
import builtins
{guard}

# === 用户代码 ===
{code}
"""

    # 写入临时文件
    tmpdir = tempfile.mkdtemp(prefix="sandbox_")
    script_path = os.path.join(tmpdir, "script.py")

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(full_code)

        start_time = time.time()
        proc = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tmpdir,
            env={"PATH": os.environ.get("PATH", ""), "TMP": tmpdir},
        )
        elapsed_ms = round((time.time() - start_time) * 1000)

        stdout = proc.stdout[:MAX_OUTPUT_BYTES]
        stderr = proc.stderr[:MAX_OUTPUT_BYTES]

        if proc.returncode == 0 and not stderr:
            return ToolResult(
                success=True,
                data={
                    "stdout": stdout,
                    "exit_code": proc.returncode,
                },
                metadata={
                    "execution_time_ms": elapsed_ms,
                    "exit_code": proc.returncode,
                },
            )
        else:
            return ToolResult(
                success=False,
                data={"stdout": stdout, "stderr": stderr},
                error=f"退出码 {proc.returncode}: {stderr[:200] if stderr else '(无错误输出)'}",
                metadata={"execution_time_ms": elapsed_ms, "exit_code": proc.returncode},
            )
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, error=f"代码执行超时（>{timeout}秒）")
    except Exception as e:
        return ToolResult(success=False, error=f"沙箱执行异常: {e}")
    finally:
        # 清理临时文件
        try:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass
```

- [ ] **Step 2: Commit**

```bash
git add workers/tools/builtin/sandbox.py
git commit -m "feat: add Python sandbox execution tool"
```

---

### Task 5: 实现 HTTP 客户端工具 (http_client.py)

**Files:**
- Create: `workers/tools/builtin/http_client.py`

- [ ] **Step 1: Create `workers/tools/builtin/http_client.py`**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add workers/tools/builtin/http_client.py
git commit -m "feat: add HTTP client tool for external API calls"
```

---

### Task 6: 更新 requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Edit `requirements.txt`**

Read `requirements.txt` and append:
```
python-docx>=1.0.0
openpyxl>=3.1.0
fpdf2>=2.7.0
requests>=2.31.0
pyyaml>=6.0
```

- [ ] **Step 2: Install dependencies**

```bash
pip install python-docx openpyxl fpdf2 requests pyyaml
```

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add tool dependencies (python-docx, openpyxl, fpdf2, requests, pyyaml)"
```

---

### Task 7: 改造 BaseWorker — 添加 _call_tool 方法

**Files:**
- Modify: `workers/base_worker.py`

- [ ] **Step 1: Edit `workers/base_worker.py`**

在 `_call_llm` 方法之后添加:

```python
    def _call_tool(self, tool_name: str, **kwargs) -> dict:
        """调用 ToolRegistry 中注册的工具并返回标准化结果。

        这是 Worker 接入真实工具能力的入口。所有 Worker 都可以通过
        此方法调用任何已注册的工具。

        Returns:
            {"success": bool, "data": ..., "error": ..., "files": [...], "metadata": {...}}
        """
        from workers.tools.registry import ToolRegistry
        result = ToolRegistry().call(tool_name, **kwargs)
        return result.to_dict()

    def _get_available_tools_prompt(self) -> str:
        """获取可用工具列表的文本描述（供 LLM prompt 使用）。"""
        from workers.tools.registry import ToolRegistry
        return ToolRegistry().get_tools_prompt()
```

- [ ] **Step 2: Commit**

```bash
git add workers/base_worker.py
git commit -m "feat: add _call_tool and _get_available_tools_prompt to BaseWorker"
```

---

### Task 8: 重写 ReportExporter — 真正写文件

**Files:**
- Modify: `workers/report_exporter.py`

- [ ] **Step 1: Rewrite `workers/report_exporter.py`**

```python
"""报告导出 Worker — 调用文件导出工具生成真实的 Word/Excel/PDF 文件"""

from workers.base_worker import BaseWorker


class ReportExporter(BaseWorker):
    """真正的报告导出器——生成 Word、Excel、PDF 文件到 outputs/ 目录。"""

    def __init__(self):
        super().__init__("ReportExporter")

    def execute(self, task: dict) -> dict:
        desc = task.get("description", "")
        result = {"worker": self.name}

        # 收集上游数据（如果 task 中有上游结果）
        upstream_data = task.get("params", {}).get("upstream_results", {})
        title = task.get("params", {}).get("title", "多智能体协同分析报告")

        # 构建报告内容
        content_lines = [f"# {title}", "", f"## 任务概述", f"", desc, ""]
        table_rows = []

        if upstream_data:
            content_lines.append("## 各Agent分析结果")
            for agent_id, agent_result in upstream_data.items():
                if isinstance(agent_result, dict):
                    output = agent_result.get("output", "") or agent_result.get("result", {}).get("output", "")
                    if output:
                        content_lines.append(f"### {agent_id}")
                        content_lines.append(output)
                        content_lines.append("")

        # 构建统计表格
        table_rows = [
            {"指标": "分析任务数", "数值": str(len(upstream_data)), "状态": "完成"},
            {"指标": "报告生成时间", "数值": "自动生成", "状态": "✅"},
            {"指标": "输出格式", "数值": "Word + Excel + PDF", "状态": "✅"},
        ]

        content = "\n".join(content_lines)
        generated_files = []

        # 1. 导出 Excel
        if table_rows:
            excel_result = self._call_tool(
                "export_excel",
                filename=f"{title}_数据汇总",
                sheets={"分析摘要": table_rows},
            )
            if excel_result.get("success"):
                generated_files.extend(excel_result.get("files", []))

        # 2. 导出 Word
        docx_result = self._call_tool(
            "export_docx",
            title=title,
            content=content,
            table_data=table_rows,
        )
        if docx_result.get("success"):
            generated_files.extend(docx_result.get("files", []))

        # 3. 导出 PDF
        pdf_result = self._call_tool(
            "export_pdf",
            title=title,
            content=content,
        )
        if pdf_result.get("success"):
            generated_files.extend(pdf_result.get("files", []))

        # 汇总输出
        file_list = "\n".join(f"- 📄 {f}" for f in generated_files) if generated_files else "（无文件生成）"
        result["output"] = (
            f"[报告导出] ✅ 已生成 {len(generated_files)} 个文件:\n{file_list}"
        )
        result["generated_files"] = generated_files
        result["export_details"] = {
            "docx": docx_result,
            "excel": excel_result,
            "pdf": pdf_result,
        }
        return result
```

- [ ] **Step 2: Commit**

```bash
git add workers/report_exporter.py
git commit -m "feat: rewrite ReportExporter to use real file export tools"
```

---

### Task 9: 改造 CodeWorker — 接入 Python 沙箱

**Files:**
- Modify: `workers/code_executor.py`

- [ ] **Step 1: Rewrite `workers/code_executor.py`**

```python
"""代码执行 Worker — 接入真实 Python 沙箱执行用户代码"""

from workers.base_worker import BaseWorker


class CodeWorker(BaseWorker):
    """真正的代码执行器——在安全沙箱中运行 Python 代码。"""

    def __init__(self):
        super().__init__("CodeWorker")

    def execute(self, task: dict) -> dict:
        desc = task.get("description", "")
        result = {"worker": self.name}

        # 从 task 中提取代码
        code = task.get("params", {}).get("code", "")
        timeout = task.get("params", {}).get("timeout", 10)

        if not code:
            # 没有代码时，用 LLM 生成代码再执行
            llm_code = self._call_llm(
                system_prompt=(
                    "你是一个Python代码生成器。根据任务描述生成简洁的Python代码。"
                    "只输出代码，不要markdown标记，不要解释。"
                    "用 print() 输出关键结果。"
                ),
                user_prompt=f"任务: {desc}\n\n生成Python代码:",
            )
            if llm_code:
                # 去除可能的 markdown 标记
                code = llm_code.strip()
                if code.startswith("```"):
                    code = "\n".join(code.split("\n")[1:-1])
            else:
                result["output"] = "[代码执行] 未提供代码且 LLM 不可用，跳过执行"
                return result

        # 调用沙箱执行
        sandbox_result = self._call_tool("run_python", code=code, timeout=timeout)

        if sandbox_result.get("success"):
            data = sandbox_result.get("data", {})
            stdout = data.get("stdout", "")
            meta = sandbox_result.get("metadata", {})
            result["output"] = (
                f"[代码执行] ✅ 沙箱执行成功\n"
                f"耗时: {meta.get('execution_time_ms', 0)}ms | 退出码: {meta.get('exit_code', 0)}\n"
                f"```\n{stdout[:500]}\n```"
            )
        else:
            data = sandbox_result.get("data", {})
            stderr = data.get("stderr", "")
            result["output"] = (
                f"[代码执行] ❌ 执行失败\n"
                f"错误: {sandbox_result.get('error', '未知错误')}\n"
                f"```\n{stderr[:300] if stderr else ''}\n```"
            )

        result["sandbox_result"] = sandbox_result
        return result
```

- [ ] **Step 2: Commit**

```bash
git add workers/code_executor.py
git commit -m "feat: rewrite CodeWorker to use real Python sandbox"
```

---

### Task 10: 新建 HTTPWorker

**Files:**
- Create: `workers/http_worker.py`

- [ ] **Step 1: Create `workers/http_worker.py`**

```python
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
                f"状态码: {data.get('status_code')} | 耗时: {meta.get('elapsed_ms', 0)}ms\n"
                f"响应: {str(data.get('body', ''))[:300]}"
            )
        else:
            result["output"] = (
                f"[HTTP请求] ❌ {method} {url}\n"
                f"错误: {http_result.get('error', '未知错误')}"
            )

        result["http_result"] = http_result
        return result
```

- [ ] **Step 2: Commit**

```bash
git add workers/http_worker.py
git commit -m "feat: add HTTPWorker for external API calls"
```

---

### Task 11: 注册 HTTPWorker 到 LangGraph 引擎

**Files:**
- Modify: `meta_agent/langgraph_engine.py`

- [ ] **Step 1: Edit TASK_TYPE_MAP and worker registration**

在 `TASK_TYPE_MAP` 常量中（约第41行），`"report_export"` 后面添加:
```python
    "http_request":    ("http_worker",       "HTTP调用", "🌐"),
```

在 `_get_workers()` 函数中（`"report_exporter": ReportExporter(),` 后面）添加:
```python
        from workers.http_worker import HTTPWorker
```

在 `_workers_cache` 字典中（`"report_exporter": ReportExporter(),` 后面）添加:
```python
            "http_worker": HTTPWorker(),
```

- [ ] **Step 2: Also update intent_parser.py TASK_TYPES**

Read `meta_agent/intent_parser.py` and add after `"report_export"` entry:
```python
    "http_request": {
        "keywords": ["API", "HTTP", "请求", "接口", "webhook", "抓取", "调用",
                     "REST", "POST", "GET", "curl", "fetch"],
        "worker": "http_worker",
        "label": "HTTP调用",
        "description_template": "发送HTTP请求调用外部API",
    },
```

- [ ] **Step 3: Commit**

```bash
git add meta_agent/langgraph_engine.py meta_agent/intent_parser.py
git commit -m "feat: register HTTPWorker in LangGraph engine and intent parser"
```

---

### Task 12: UI — 右侧面板添加文件下载区域

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add download area in right panel**

在右侧面板的工作流结果显示之后，st.markdown('</div>', unsafe_allow_html=True) 之前，添加下载区域代码。

定位到第763行 `st.markdown('</div>', unsafe_allow_html=True)` 之前，插入：

```python
        # 文件下载区域
        all_files = []
        for tid in sorted(results.keys()):
            r = results[tid]
            if r.get("status") != "success":
                continue
            result_data = r.get("result", {})
            if not isinstance(result_data, dict):
                continue
            files = result_data.get("generated_files", [])
            if files:
                all_files.extend(files)

        if all_files:
            st.markdown("#### 📥 下载报告文件")
            import base64
            import zipfile
            import io

            for fpath in all_files:
                fname = fpath.replace("\\", "/").split("/")[-1]
                try:
                    with open(fpath, "rb") as f:
                        fdata = f.read()
                    fsize_kb = round(len(fdata) / 1024, 1)
                    ext = fname.rsplit(".", 1)[-1] if "." in fname else ""
                    icon = {"docx": "📄", "xlsx": "📊", "pdf": "📕"}.get(ext, "📎")
                    col1, col2, col3 = st.columns([0.4, 0.3, 0.3])
                    col1.caption(f"{icon} {fname}")
                    col2.caption(f"{fsize_kb} KB")
                    col3.download_button(
                        label=f"下载",
                        data=fdata,
                        file_name=fname,
                        mime={
                            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "pdf": "application/pdf",
                        }.get(ext, "application/octet-stream"),
                        key=f"dl_{fname}",
                        use_container_width=True,
                    )
                except Exception:
                    st.caption(f"⚠️ 无法读取: {fname}")

            # 打包下载
            if len(all_files) > 1:
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for fpath in all_files:
                        fname = fpath.replace("\\", "/").split("/")[-1]
                        try:
                            with open(fpath, "rb") as f:
                                zf.writestr(fname, f.read())
                        except Exception:
                            pass
                st.download_button(
                    label="📦 打包下载全部文件 (ZIP)",
                    data=zip_buf.getvalue(),
                    file_name="analysis_report_pack.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
```

- [ ] **Step 2: Commit**

```bash
git add app.py
git commit -m "feat: add file download area to result panel"
```

---

### Task 13: 添加 tools.yaml 配置加载支持

**Files:**
- Create: `workers/tools/tools.yaml`
- Modify: `workers/tools/registry.py`

- [ ] **Step 1: Create `workers/tools/tools.yaml`**

```yaml
# 外部工具配置 — 非Python开发者可通过此文件注册工具
# 系统启动时自动加载

tools:
  # 示例: HTTP API 工具
  # - name: get_weather
  #   description: 获取指定城市的天气信息
  #   type: http
  #   endpoint: https://api.weather.com/v1/current
  #   method: GET
  #   headers:
  #     Authorization: Bearer ${WEATHER_API_KEY}

  # 示例: 脚本工具
  # - name: run_data_pipeline
  #   description: 执行数据处理流水线
  #   type: script
  #   command: python scripts/data_pipeline.py
```

- [ ] **Step 2: Add YAML loading to registry.py**

在 `registry.py` 文件末尾添加:

```python
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
```

- [ ] **Step 3: Auto-load YAML tools on import**

在 `workers/tools/__init__.py` 末尾添加:

```python
# 自动加载 tools.yaml 中配置的外部工具
from workers.tools.registry import load_tools_from_yaml
load_tools_from_yaml()
```

- [ ] **Step 4: Commit**

```bash
git add workers/tools/tools.yaml workers/tools/registry.py workers/tools/__init__.py
git commit -m "feat: add YAML-based external tool registration"
```

---

### Task 14: 集成验证 — 端到端测试

- [ ] **Step 1: Run the app to verify**

```bash
streamlit run app.py
```

验证清单:
- [ ] 输入"分析上海房价趋势并导出报告"→ 工作流完成后右侧出现下载按钮
- [ ] 点击下载按钮可下载 Word/Excel/PDF 文件
- [ ] 输入"写一段Python代码计算斐波那契数列"→ CodeWorker 沙箱执行并返回结果
- [ ] 输入"调用 https://httpbin.org/json API"→ HTTPWorker 发送请求并返回响应
- [ ] 检查 `outputs/` 目录有真实生成的文件

- [ ] **Step 2: Commit if any fixes**

```bash
git add -A
git commit -m "fix: end-to-end integration fixes"
```

---

**Plan complete.** Total: 14 tasks, estimated ~2 hours implementation time.
