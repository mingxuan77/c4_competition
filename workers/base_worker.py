"""Worker 抽象基类 - 定义统一的执行接口，支持模拟与LLM双模式"""

import time
import random
from abc import ABC, abstractmethod
from config import WORKER_CONFIG, LLM_CONFIG, get_llm_client


class BaseWorker(ABC):
    """所有 Worker 的抽象基类。"""

    def __init__(self, name: str):
        self.name = name
        self.min_delay = WORKER_CONFIG["mock_delay_min"]
        self.max_delay = WORKER_CONFIG["mock_delay_max"]
        self.failure_rate = WORKER_CONFIG["mock_failure_rate"]

    @abstractmethod
    def execute(self, task: dict) -> dict:
        """执行任务并返回结果。task: {"task_id": "A", "task_type": "...", "params": {...}}"""
        ...

    def _simulate_work(self, description: str = "") -> dict:
        """模拟工作延迟，返回基础结果结构。"""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)

        if random.random() < self.failure_rate:
            raise RuntimeError(f"{self.name} 执行模拟失败")

        return {
            "worker": self.name,
            "execution_time_seconds": round(delay, 2),
        }

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str | None:
        """调用 LLM 生成专业分析结果。如果 LLM 不可用返回 None。"""
        client = get_llm_client()
        if not client:
            return None
        try:
            response = client.chat.completions.create(
                model=LLM_CONFIG["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                max_tokens=600,
            )
            return response.choices[0].message.content
        except Exception:
            return None
