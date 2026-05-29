"""网络监控 Worker"""

from workers.base_worker import BaseWorker


class NetworkWorker(BaseWorker):
    def __init__(self):
        super().__init__("NetworkWorker")

    def execute(self, task: dict) -> dict:
        result = self._simulate_work(task.get("description", ""))
        desc = task.get("description", "")
        llm_output = self._call_llm(
            system_prompt="你是网络工程师。简洁输出：拓扑/流量发现、瓶颈、优化建议。用中文，100-200字。",
            user_prompt=f"分析: {desc}",
        )
        result["output"] = llm_output if llm_output else f"[网络分析] 完成"
        return result
