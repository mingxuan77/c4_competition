"""报告导出 Worker — 综合上游Agent结果，生成内容充实的 Word/Excel/PDF 文件"""

from workers.base_worker import BaseWorker


class ReportExporter(BaseWorker):
    """真正的报告导出器——将上游所有Agent的分析结果写入Word、Excel、PDF。"""

    def __init__(self):
        super().__init__("ReportExporter")

    def execute(self, task: dict) -> dict:
        desc = task.get("description", "")
        title = task.get("params", {}).get("title", "多智能体协同分析报告")
        upstream = task.get("params", {}).get("upstream_results", {})

        # ── 收集所有上游Agent的输出 ──
        content_lines = [
            f"# {title}",
            "",
            "## 一、任务概述",
            "",
            desc,
            "",
            "## 二、各Agent分析结果",
            "",
        ]

        table_rows = []
        agent_idx = 1
        for agent_id, agent_result in upstream.items():
            if not isinstance(agent_result, dict):
                continue
            output = agent_result.get("output", "")
            if not output:
                continue

            content_lines.append(f"### {agent_idx}. {agent_id}")
            content_lines.append(output)
            content_lines.append("")

            # 提取摘要用于表格
            summary = output[:80].replace("\n", " ") + ("..." if len(output) > 80 else "")
            table_rows.append({
                "序号": agent_idx,
                "Agent": agent_id,
                "输出摘要": summary,
                "状态": "✅ 完成",
            })
            agent_idx += 1

        # 如果没有上游结果，至少放一些有意义的内容
        if not content_lines[5:]:  # 只有标题和概述
            content_lines.append("（本次分析未包含子Agent详细输出）")
            content_lines.append("")

        # 添加总结段
        content_lines.append("## 三、总结")
        content_lines.append("")
        content_lines.append(
            f"本报告由 Meta-Agent 多智能体协同调度系统自动生成，"
            f"共调度 {len(upstream)} 个专业Agent协同完成分析任务。"
            f"各Agent分工明确，输出内容涵盖数据检索、分析建模、"
            f"策略建议等多个维度，形成完整的分析链路。"
        )
        content_lines.append("")

        if not table_rows:
            table_rows = [{
                "序号": 1,
                "Agent": "系统",
                "输出摘要": f"共完成 {len(upstream)} 个分析任务",
                "状态": "✅",
            }]

        content = "\n".join(content_lines)
        generated_files = []

        # ── 1. Excel 数据汇总 ──
        excel_result = self._call_tool(
            "export_excel",
            filename=f"{title}_数据汇总",
            sheets={"Agent输出摘要": table_rows},
        )
        if excel_result.get("success"):
            generated_files.extend(excel_result.get("files", []))

        # ── 2. Word 完整报告 ──
        docx_result = self._call_tool(
            "export_docx",
            title=title,
            content=content,
            table_data=table_rows,
        )
        if docx_result.get("success"):
            generated_files.extend(docx_result.get("files", []))

        # ── 3. PDF 完整报告 ──
        pdf_result = self._call_tool(
            "export_pdf",
            title=title,
            content=content,
        )
        if pdf_result.get("success"):
            generated_files.extend(pdf_result.get("files", []))

        # 汇总输出
        file_names = [f.replace("\\", "/").split("/")[-1] for f in generated_files]
        file_list = "\n".join(f"- {n}" for n in file_names) if file_names else "（无文件生成）"

        result = {"worker": self.name}
        result["output"] = (
            f"[报告导出] ✅ 已生成 {len(generated_files)} 个文件（包含 {len(upstream)} 个Agent的完整分析内容）:\n{file_list}"
        )
        result["generated_files"] = generated_files
        result["export_details"] = {
            "docx": docx_result,
            "excel": excel_result,
            "pdf": pdf_result,
        }
        return result
