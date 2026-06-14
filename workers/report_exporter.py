"""报告导出 Worker — 将分析结果导出为Word文件"""

from workers.base_worker import BaseWorker


class ReportExporter(BaseWorker):
    """报告导出器——生成Word(.docx)文件到 outputs/ 目录。"""

    def __init__(self):
        super().__init__("ReportExporter")

    def execute(self, task: dict) -> dict:
        desc = task.get("description", "")
        title = task.get("params", {}).get("title", "产线分析报告")
        upstream = task.get("params", {}).get("upstream_results", {})

        # ── 收集上游Agent输出，构建报告内容 ──
        content_lines = [
            f"# {title}",
            "",
            desc,
            "",
            "## 分析结果",
            "",
        ]

        for agent_id, agent_result in upstream.items():
            if not isinstance(agent_result, dict):
                continue
            output = agent_result.get("output", "")
            if not output:
                continue
            content_lines.append(output)
            content_lines.append("")

        if len(content_lines) <= 6:
            content_lines.append("（本次分析未包含详细Agent输出）")
            content_lines.append("")

        content = "\n".join(content_lines)
        generated_files = []

        # ── 仅导出 Word ──
        docx_result = self._call_tool(
            "export_docx",
            title=title,
            content=content,
        )
        if docx_result.get("success"):
            generated_files.extend(docx_result.get("files", []))

        file_names = [f.replace("\\", "/").split("/")[-1] for f in generated_files]
        file_list = "\n".join(f"- {n}" for n in file_names) if file_names else "（无文件生成）"

        result = {"worker": self.name}
        result["output"] = (
            f"✅ 报告已生成: {', '.join(file_names)}" if file_names else "报告生成失败"
        )
        result["generated_files"] = generated_files
        return result
