"""安全分析 Worker"""

from workers.base_worker import BaseWorker


class SecurityWorker(BaseWorker):
    def __init__(self):
        super().__init__("SecurityWorker")

    def execute(self, task: dict) -> dict:
        result = self._simulate_work(task.get("description", ""))
        desc = task.get("description", "")
        llm_output = self._call_llm(
            system_prompt="你是安全专家。简洁输出：漏洞/风险发现、修复建议。用中文，100-200字。",
            user_prompt=f"分析: {desc}",
        )
        result["output"] = llm_output if llm_output else f"[安全分析] 完成"
        return result
