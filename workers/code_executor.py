"""代码执行 Worker - 负责安全沙箱内运行用户代码/脚本"""

from workers.base_worker import BaseWorker


class CodeWorker(BaseWorker):
    def __init__(self):
        super().__init__("CodeWorker")

    def execute(self, task: dict) -> dict:
        result = self._simulate_work(task.get("description", ""))
        result["execution"] = {
            "language": "Python 3.12",
            "sandbox": "Docker + cgroup v2",
            "exit_code": 0,
            "execution_time_ms": 234,
            "memory_peak_mb": 45.6,
            "stdout_preview": "结果已输出到 /sandbox/result.json",
        }
        result["output"] = (
            f"[代码执行] {result['execution']['language']} 沙箱执行完成, "
            f"耗时 {result['execution']['execution_time_ms']}ms, "
            f"内存峰值 {result['execution']['memory_peak_mb']}MB, 退出码 0"
        )
        return result
