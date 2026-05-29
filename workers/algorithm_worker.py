"""算法 Worker"""

from workers.base_worker import BaseWorker


class AlgorithmWorker(BaseWorker):
    def __init__(self):
        super().__init__("AlgorithmWorker")

    def execute(self, task: dict) -> dict:
        result = self._simulate_work(task.get("description", ""))
        desc = task.get("description", "")

        llm_output = self._call_llm(
            system_prompt="你是算法工程师。简洁输出分析结果：方法、排名/匹配结果、指标。用中文，100-200字。",
            user_prompt=f"分析: {desc}",
        )

        if llm_output:
            result["output"] = llm_output
        else:
            result["output"] = f"[算法分析] 完成"
        return result
