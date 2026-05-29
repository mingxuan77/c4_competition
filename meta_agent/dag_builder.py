"""DAG 构建器 - 基于邻接表结构构建任务依赖图"""

from utils.graph_utils import build_adjacency_list


class DAGBuilder:
    """将标准化任务列表构建为邻接表 DAG。"""

    def build(self, tasks: list[dict]) -> dict[str, dict]:
        """构建并返回邻接表结构的 DAG。

        返回: {task_id: {"deps": [...], "next": [...], "indegree": int, "data": {...}}}
        """
        adj = build_adjacency_list(tasks)

        # 环检测：拓扑排序后检查是否有未处理节点
        from utils.graph_utils import kahn_topological_sort
        layers = kahn_topological_sort(adj)
        sorted_count = sum(len(layer) for layer in layers)
        if sorted_count != len(adj):
            raise ValueError("任务依赖图中存在环路，无法构建 DAG")

        return adj

    def to_task_list(self, adj: dict[str, dict]) -> list[dict]:
        """从邻接表中提取任务列表（便于传递给调度器）。"""
        tasks = []
        for tid, node in adj.items():
            task = dict(node["data"])
            task["deps"] = node["deps"]
            tasks.append(task)
        return tasks
