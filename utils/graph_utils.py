"""图结构工具 - 邻接表存储 + 拓扑排序 + 并行度分析"""

from collections import deque


def build_adjacency_list(tasks: list[dict]) -> dict[str, dict]:
    """将任务列表构建为邻接表结构的 DAG。

    tasks: [{"task_id": "A", "deps": [], "task_type": "retrieval", ...}, ...]
    返回: {task_id: {"deps": [...], "next": [...], "indegree": int, "data": {...}}}
    """
    adj = {}
    for t in tasks:
        tid = t["task_id"]
        adj[tid] = {
            "deps": list(t.get("deps", [])),
            "next": [],
            "indegree": len(t.get("deps", [])),
            "data": t,
        }
    for tid, node in adj.items():
        for dep_id in node["deps"]:
            if dep_id in adj:
                adj[dep_id]["next"].append(tid)
    return adj


def kahn_topological_sort(adj: dict[str, dict]) -> list[list[str]]:
    """Kahn 拓扑排序，返回分层执行计划。
    每层内部的任务可并行执行。
    """
    indegree = {tid: adj[tid]["indegree"] for tid in adj}
    queue = deque([tid for tid, d in indegree.items() if d == 0])
    layers = []

    while queue:
        layer = list(queue)
        layers.append(layer)
        queue.clear()
        for tid in layer:
            for next_id in adj[tid]["next"]:
                indegree[next_id] -= 1
                if indegree[next_id] == 0:
                    queue.append(next_id)

    return layers


def get_parallel_groups(adj: dict[str, dict]) -> list[list[str]]:
    """获取可并行执行的任务分组。"""
    return kahn_topological_sort(adj)
