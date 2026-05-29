
"""任务规划器 - 将意图解析结果标准化为可执行的任务列表"""


class TaskPlanner:
    """将意图解析结果转换为标准化的子任务列表。"""

    def plan(self, intent_result: dict) -> list[dict]:
        """生成标准子任务列表，每个任务包含依赖信息。

        返回: [
            {
                "task_id": "A",
                "task_type": "retrieval",
                "description": "...",
                "deps": [],
                "params": {"query": "..."},
            },
            ...
        ]
        """
        tasks = intent_result.get("tasks", [])
        dependencies = intent_result.get("dependencies", {})

        planned = []
        for task in tasks:
            tid = task["task_id"]
            planned.append({
                "task_id": tid,
                "task_type": task["type"],
                "description": task.get("description", ""),
                "deps": dependencies.get(tid, []),
                "params": task.get("params", {}),
            })

        return planned
