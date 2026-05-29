"""策略输出 Worker - 根据任务内容自适应角色，生成最终策略报告"""

from workers.base_worker import BaseWorker


class StrategyWorker(BaseWorker):
    def __init__(self):
        super().__init__("StrategyWorker")

    def execute(self, task: dict) -> dict:
        result = self._simulate_work(task.get("description", ""))
        desc = task.get("description", "")

        llm_output = self._call_llm(
            system_prompt=f"""你是一个专业的策略分析师。根据任务描述，自适应角色并给出具体建议。

任务: {desc}

要求: 给出具体可操作的建议，每条建议包含: 行动方案、理由、优先级(P0/P1/P2)。
直接输出分析结论，不输出模板框架。用中文，300~500字。""",
            user_prompt=f"请基于此任务生成策略建议。不要套用模板，根据任务内容具体分析。",
        )

        if llm_output:
            result["strategy"] = {
                "title": "分析报告",
                "executive_summary": llm_output[:300],
                "recommendations": [],
                "risk_assessment": {"overall_risk_level": "详见分析"},
                "conclusion": llm_output,
            }
            result["output"] = llm_output
        else:
            result["output"] = f"[策略输出] 基于「{desc[:50]}」的分析已完成"
        return result
