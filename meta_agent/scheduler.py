"""任务调度器 - 基于拓扑排序的并行任务调度"""

import time
import threading
from utils.graph_utils import kahn_topological_sort

TASK_TYPE_MAP = {
    "retrieval": ("retrieval_worker", "数据检索", "🔍"),
    "data_processing": ("data_worker", "数据处理", "🧹"),
    "ml_prediction": ("ml_worker", "机器学习", "🤖"),
    "algorithm": ("algorithm_worker", "算法优化", "⚙️"),
    "security": ("security_worker", "安全分析", "🛡️"),
    "code_execution": ("code_worker", "代码执行", "💻"),
    "network": ("network_worker", "网络监控", "🌐"),
    "database": ("database_worker", "数据库", "🗄️"),
    "strategy": ("strategy_worker", "策略输出", "📊"),
    "report": ("strategy_worker", "报告生成", "📊"),
    "report_export": ("report_exporter", "报告导出", "📄"),
}


class Scheduler:
    """Kahn 拓扑排序调度器，支持并行层执行。"""

    def __init__(self, workers: dict, logger=None):
        self.workers = workers
        self.logger = logger

    def _select_worker(self, task_type: str):
        if task_type in TASK_TYPE_MAP:
            worker_name = TASK_TYPE_MAP[task_type][0]
            return self.workers.get(worker_name)
        return self.workers.get("algorithm_worker")

    def _execute_task(self, task: dict, results: dict, adj: dict):
        tid = task["task_id"]
        task_type = task.get("task_type", "")
        worker_name, type_label, icon = TASK_TYPE_MAP.get(task_type, ("unknown", task_type, ""))

        if self.logger:
            self.logger.info(
                f"调度 → {icon} {type_label} Agent [{worker_name}] 执行: {task.get('description', tid)}",
                task_id=tid,
            )

        adj[tid]["data"]["status"] = "running"
        adj[tid]["data"]["worker_name"] = worker_name
        adj[tid]["data"]["type_label"] = type_label
        adj[tid]["data"]["start_time"] = time.strftime("%H:%M:%S")

        try:
            worker = self._select_worker(task_type)
            if worker:
                result = worker.execute(task)
                results[tid] = {"status": "success", "result": result,
                                "worker_name": worker_name, "type_label": type_label}
                adj[tid]["data"]["status"] = "completed"
                adj[tid]["data"]["end_time"] = time.strftime("%H:%M:%S")
                if self.logger:
                    self.logger.success(
                        f"[{type_label}] {worker_name} 完成: {task.get('description', tid)}",
                        task_id=tid,
                    )
            else:
                results[tid] = {"status": "skipped", "result": {"output": "无可用Worker"},
                                "worker_name": "-", "type_label": type_label}
                adj[tid]["data"]["status"] = "completed"
                if self.logger:
                    self.logger.warning(f"无可用Worker: {tid}", task_id=tid)
        except Exception as e:
            results[tid] = {"status": "failed", "result": {"output": str(e)},
                            "worker_name": worker_name, "type_label": type_label}
            adj[tid]["data"]["status"] = "failed"
            if self.logger:
                self.logger.error(f"执行失败: {e}", task_id=tid)

    def run(self, adj: dict[str, dict]) -> dict[str, dict]:
        layers = kahn_topological_sort(adj)
        results = {}

        # ─── DAG 结构日志 ───
        if self.logger:
            self.logger.info(f"═════ 调度计划: {len(layers)} 层, 共 {sum(len(l) for l in layers)} 个任务 ═════")
            for i, layer in enumerate(layers):
                parallel_mark = " ∥ 并行" if len(layer) > 1 else " → 串行"
                for tid in layer:
                    task_data = adj[tid]["data"]
                    task_type = task_data.get("task_type", "")
                    _, type_label, icon = TASK_TYPE_MAP.get(task_type, ("", task_type, ""))
                    desc = task_data.get("description", "")
                    deps = adj[tid].get("deps", [])
                    next_ids = adj[tid].get("next", [])
                    dep_str = f" (依赖: {', '.join(deps)})" if deps else ""
                    next_str = f" (后继: {', '.join(next_ids)})" if next_ids else ""
                    self.logger.info(
                        f"  L{i+1}{parallel_mark} | 节点 {tid} | {icon} {type_label} | {desc}{dep_str}{next_str}",
                        task_id=tid,
                    )
                if len(layer) > 1:
                    self.logger.info(f"  └─ L{i+1} 层内 {len(layer)} 个任务可并行执行", task_id=None)

        for layer_idx, layer in enumerate(layers):
            threads = []
            for tid in layer:
                adj[tid]["data"]["layer"] = layer_idx + 1

            for tid in layer:
                task = adj[tid]["data"]
                t = threading.Thread(target=self._execute_task, args=(task, results, adj))
                t.start()
                threads.append((tid, t))

            for tid, t in threads:
                t.join()

        return results
