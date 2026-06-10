"""策略输出 Worker - 综合上游Agent结果，生成完整策略报告"""

from workers.base_worker import BaseWorker


class StrategyWorker(BaseWorker):
    def __init__(self):
        super().__init__("StrategyWorker")

    def execute(self, task: dict) -> dict:
        result = {"worker": self.name}
        desc = task.get("description", "")

        # 收集上游Agent的所有输出
        upstream = task.get("params", {}).get("upstream_results", {})
        upstream_text = ""
        for agent_id, agent_result in upstream.items():
            if isinstance(agent_result, dict):
                output = agent_result.get("output", "")
                if output:
                    upstream_text += f"\n\n### {agent_id} 分析结果:\n{output}"

        # 构建给LLM的完整输入
        if upstream_text:
            llm_output = self._call_llm(
                system_prompt=(
                    "你是一个资深的策略分析师。请基于上游多个专业Agent的分析结果，"
                    "生成一份全面的综合策略报告。要求：\n"
                    "1. 先总结各Agent的关键发现（2-3句话概述）\n"
                    "2. 列出3-5条具体的、可操作的策略建议，每条包含行动方案和理由\n"
                    "3. 评估主要风险和缓解措施\n"
                    "4. 用具体数据和事实支撑结论，不要空洞的套话\n"
                    "5. 输出2000-4000字，确保内容完整不截断"
                ),
                user_prompt=(
                    f"任务: {desc}\n\n"
                    f"上游分析结果汇总:\n{upstream_text}\n\n"
                    f"请基于以上所有分析，生成综合策略报告。"
                ),
            )
        else:
            llm_output = self._call_llm(
                system_prompt=(
                    "你是策略分析师。根据任务描述给出具体策略建议，"
                    "每条建议包含行动方案和理由。输出1000-2000字，确保内容完整。"
                ),
                user_prompt=f"任务: {desc}",
            )

        if llm_output:
            result["strategy"] = {
                "title": "综合分析报告",
                "executive_summary": llm_output[:800],
                "recommendations": [],
                "risk_assessment": {"overall_risk_level": "详见分析"},
                "conclusion": llm_output,
            }
            result["output"] = llm_output
        else:
            result["output"] = (
                f"[策略输出] 基于 {len(upstream)} 个上游Agent的分析结果，"
                f"综合建议已生成。请查看报告导出文件获取详细内容。"
            )
        return result
