"""报告导出 Worker — 调用文件导出工具生成真实的 Word/Excel/PDF 文件"""

from workers.base_worker import BaseWorker


class ReportExporter(BaseWorker):
    """真正的报告导出器——生成 Word、Excel、PDF 文件到 outputs/ 目录。"""

    def __init__(self):
        super().__init__("ReportExporter")

    def execute(self, task: dict) -> dict:
        desc = task.get("description", "")
        result = {"worker": self.name}

        # 收集上游数据
        upstream_data = task.get("params", {}).get("upstream_results", {})
        title = task.get("params", {}).get("title", "多智能体协同分析报告")

        # 构建报告内容
        content_lines = [f"# {title}", "", "## 任务概述", "", desc, ""]

        if upstream_data:
            content_lines.append("## 各Agent分析结果")
            for agent_id, agent_result in upstream_data.items():
                if isinstance(agent_result, dict):
                    output = (
                        agent_result.get("output", "")
                        or agent_result.get("result", {}).get("output", "")
                    )
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
        file_list = "\n".join(
            f"- 📄 {f}" for f in generated_files
        ) if generated_files else "（无文件生成）"

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
