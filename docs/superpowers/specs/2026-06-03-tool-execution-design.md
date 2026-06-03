# 真实工具执行能力 — 设计文档

**日期**: 2026-06-03
**状态**: 已确认，进入实现

## 目标

让多智能体系统从"Prompt编辑器"变成能真正调用外部工具完成端到端任务的系统。

## 核心设计

### 1. ToolRegistry — 工具注册中心

新增 `workers/tools/` 模块，提供统一的工具注册、发现、调用机制。

```
workers/tools/
├── __init__.py          # 导出 ToolRegistry、@tool 装饰器
├── registry.py          # ToolRegistry 单例：注册/发现/调用/Schema校验
├── builtin/
│   ├── file_export.py   # export_docx, export_excel, export_pdf
│   ├── sandbox.py       # run_python 沙箱
│   └── http_client.py   # http_request
└── schema.py            # ToolParam, ToolResult 数据结构
```

#### 工具注册方式

**方式1: 装饰器（Python开发者）**
```python
from workers.tools import tool

@tool(name="export_excel", description="导出Excel文件",
      parameters={"data": "导出数据", "filename": "文件名"})
def export_excel(data, filename) -> ToolResult:
    ...
```

**方式2: YAML配置（非Python开发者）**
```yaml
# tools.yaml
tools:
  - name: my_api
    description: 调用业务API
    type: http
    endpoint: https://api.example.com/execute
```

### 2. 内置工具

| 工具 | 功能 | 依赖库 |
|------|------|--------|
| export_docx | Word报告导出（目录/标题/表格/模板） | python-docx |
| export_excel | Excel导出（多Sheet/图表/公式/格式化） | openpyxl |
| export_pdf | PDF导出（分页/页眉页脚） | fpdf2 |
| run_python | Python沙箱执行（隔离/超时/安全限制） | subprocess |
| http_request | HTTP API调用（GET/POST/PUT/DELETE） | requests |

### 3. Worker改造

- 保留现有10个Worker不变
- ExportWorker → 接入 ToolRegistry，真正写文件
- CodeWorker → 接入 run_python 沙箱
- 新增 HTTPWorker → 接入 http_request
- 其他Worker保持现有逻辑，后续逐步接入工具

### 4. UI增强

- 工作流结果面板底部新增下载区域
- 文件列表 + 下载按钮
- 支持打包下载（zip）

### 5. 与现有系统的关系（增量，不替换）

- IntentParser: 不变
- TaskPlanner: 不变
- LangGraph Engine: 不变
- Streamlit UI: 追加下载区域，其余不变
- BaseWorker: 新增 `_call_tool()` 方法，现有 `_call_llm()` 和 `_simulate_work()` 保留
- 原有9个Worker: 全部保留，不做破坏性修改

## 实现顺序

1. ToolRegistry 核心（registry.py + schema.py + @tool装饰器）
2. 三个文件导出工具（export_docx, export_excel, export_pdf）
3. Python沙箱（run_python）
4. HTTP客户端（http_request）
5. 改造 ExportWorker、CodeWorker，新增 HTTPWorker
6. UI下载区域
7. tools.yaml 配置加载
