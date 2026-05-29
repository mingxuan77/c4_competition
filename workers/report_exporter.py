"""报告导出 Worker - 负责生成 Markdown 表格、HTML 报告、模拟 PDF 导出"""

import json
from workers.base_worker import BaseWorker


class ReportExporter(BaseWorker):
    def __init__(self):
        super().__init__("ReportExporter")

    def execute(self, task: dict) -> dict:
        result = self._simulate_work(task.get("description", ""))

        # 生成示例统计表格
        stats_table = {
            "columns": ["指标", "当前值", "目标值", "提升幅度"],
            "rows": [
                ["安全合规评分", "78.5/100", "95+/100", "+21%"],
                ["网络P95延迟", "14.7ms", "<8ms", "-46%"],
                ["数据库查询延迟", "2,100ms", "<200ms", "-90%"],
                ["投资组合年化收益", "5.5%", "8.7%", "+58%"],
                ["系统可用性", "99.5%", "99.95%", "+0.45%"],
                ["MTTR(平均修复时间)", "4小时", "15分钟", "-94%"],
            ],
        }

        # 生成 Markdown 格式报告
        md_report = self._build_markdown_report(stats_table, task)

        # 生成 HTML 格式报告
        html_report = self._build_html_report(stats_table, task)

        # 模拟 PDF 导出元信息
        pdf_meta = {
            "filename": f"analysis_report_{task.get('task_id', 'output')}.pdf",
            "pages": 12,
            "size_kb": 842,
            "sections": ["执行摘要", "数据分析", "建模结果", "策略建议", "风险评估", "附录"],
            "generated": True,
        }

        result["stats_table"] = stats_table
        result["markdown_report"] = md_report[:500] + "..."
        result["html_report"] = html_report[:500] + "..."
        result["pdf_export"] = pdf_meta
        result["output"] = (
            f"[报告导出] 已生成 3 种格式: "
            f"Markdown({len(md_report)}字符) | HTML({len(html_report)}字符) | "
            f"PDF({pdf_meta['pages']}页, {pdf_meta['size_kb']}KB)"
        )
        return result

    def _build_markdown_report(self, table: dict, task: dict) -> str:
        header = "| " + " | ".join(table["columns"]) + " |"
        sep = "|" + "|".join([" --- " for _ in table["columns"]]) + "|"
        rows = "\n".join("| " + " | ".join(row) + " |" for row in table["rows"])
        return f"""# 多智能体协同分析报告

## 概述
本报告由 Meta-Agent 调度 10 个异构智能体协同生成。

## 关键指标汇总
{header}
{sep}
{rows}

## 结论
系统已完成全流程分析，具体策略建议请参见策略输出部分。
"""

    def _build_html_report(self, table: dict, task: dict) -> str:
        thead = "<tr>" + "".join(f"<th>{c}</th>" for c in table["columns"]) + "</tr>"
        tbody = "\n".join(
            "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
            for row in table["rows"]
        )
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>分析报告</title>
<style>body{{font-family:'Microsoft YaHei',sans-serif;margin:40px}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ddd;padding:12px;text-align:left}}
th{{background:#4A90D9;color:white}}</style></head>
<body><h1>多智能体协同分析报告</h1>
<table>{thead}{tbody}</table>
<p><em>由 Meta-Agent 多智能体协同调度系统自动生成</em></p>
</body></html>"""
