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

        # 判断是否为产线相关任务
        is_production = any(kw in desc for kw in ["产线", "光刻", "刻蚀", "测试", "良率", "产能", "DPPM", "OEE"])

        if upstream_text:
            if is_production:
                system_prompt = (
                    "你是半导体制造工艺工程师。基于产线监控数据，聚焦实际状况给出分析。"
                    "要求：\n"
                    "1. 直接分析当前三条产线的状态数据，指出具体异常指标和数值\n"
                    "2. 给出1-3条针对性建议，每条必须具体到产线+参数+调整量\n"
                    "3. 不要讲套话、不要重复数据摘要、不要写'调度了X个Agent'之类的元信息\n"
                    "4. 字数控制在500-800字，简洁专业"
                )
            else:
                system_prompt = (
                    "你是策略分析师。基于上游分析结果，给出具体可操作的建议。"
                    "要求：简洁直接，用数据说话，500-800字。"
                )
            llm_output = self._call_llm(
                system_prompt=system_prompt,
                user_prompt=(
                    f"任务: {desc}\n\n"
                    f"上游分析结果汇总:\n{upstream_text}\n\n"
                    f"请基于以上数据给出分析结论。"
                ),
            )
        else:
            llm_output = self._call_llm(
                system_prompt="你是策略分析师。根据任务描述给出简洁建议。200-500字。",
                user_prompt=f"任务: {desc}",
            )

        if llm_output:
            result["strategy"] = {
                "title": "综合分析结果",
                "executive_summary": llm_output[:800],
                "recommendations": [],
                "risk_assessment": {"overall_risk_level": "详见分析"},
                "conclusion": llm_output,
            }
            result["output"] = llm_output
        else:
            result["output"] = (
                f"[策略输出] 基于 {len(upstream)} 个上游Agent的分析结果，"
                f"已生成综合分析结论与建议。"
            )
        return result
