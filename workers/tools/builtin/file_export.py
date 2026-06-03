"""文件导出工具: Word(.docx), Excel(.xlsx), PDF(.pdf)"""

import os
import time
from datetime import datetime
from workers.tools.registry import tool
from workers.tools.schema import ToolResult

_OUTPUT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "outputs")
)


def _ensure_output_dir():
    os.makedirs(_OUTPUT_DIR, exist_ok=True)
    return _OUTPUT_DIR


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
            metadata={
                "filename": os.path.basename(filepath),
                "size_kb": round(file_size / 1024, 1),
                "sheets": list(sheets.keys()),
            },
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
        pdf.cell(0, 8, f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                 new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.cell(0, 8, "由 Meta-Agent 多智能体协同调度系统自动生成",
                 new_x="LMARGIN", new_y="NEXT", align="C")
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
                pdf.cell(8, 8, "-")
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
