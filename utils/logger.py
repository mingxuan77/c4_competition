"""简易日志工具"""

import time
from typing import Callable


class ExecutionLogger:
    """收集执行过程中的日志和事件。"""

    def __init__(self):
        self.logs: list[dict] = []
        self._callback: Callable | None = None

    def set_callback(self, cb: Callable):
        self._callback = cb

    def log(self, level: str, message: str, task_id: str | None = None):
        entry = {
            "timestamp": time.strftime("%H:%M:%S"),
            "level": level,
            "message": message,
            "task_id": task_id,
        }
        self.logs.append(entry)
        if self._callback:
            self._callback(entry)

    def info(self, message: str, task_id: str | None = None):
        self.log("INFO", message, task_id)

    def success(self, message: str, task_id: str | None = None):
        self.log("SUCCESS", message, task_id)

    def error(self, message: str, task_id: str | None = None):
        self.log("ERROR", message, task_id)

    def warning(self, message: str, task_id: str | None = None):
        self.log("WARNING", message, task_id)
