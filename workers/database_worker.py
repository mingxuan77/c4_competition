"""数据库 Worker"""

from workers.base_worker import BaseWorker


class DatabaseWorker(BaseWorker):
    def __init__(self):
        super().__init__("DatabaseWorker")

    def execute(self, task: dict) -> dict:
        result = self._simulate_work(task.get("description", ""))
        desc = task.get("description", "")
        llm_output = self._call_llm(
            system_prompt="你是DBA。简洁输出：查询/迁移分析、性能优化建议。用中文，100-200字。",
            user_prompt=f"分析: {desc}",
        )
        result["output"] = llm_output if llm_output else f"[数据库分析] 完成"
        return result
