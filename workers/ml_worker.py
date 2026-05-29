"""机器学习 Worker"""

from workers.base_worker import BaseWorker


class MLWorker(BaseWorker):
    def __init__(self):
        super().__init__("MLWorker")

    def execute(self, task: dict) -> dict:
        result = self._simulate_work(task.get("description", ""))
        desc = task.get("description", "")

        llm_output = self._call_llm(
            system_prompt="你是数据分析师。简洁输出分析结果：关键发现、指标、趋势。用中文，100-200字。",
            user_prompt=f"分析: {desc}",
        )

        if llm_output:
            result["output"] = llm_output
        else:
            result["output"] = f"[ML分析] 完成"
        return result
