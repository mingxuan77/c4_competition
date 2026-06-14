"""单条产线状态机 — 产能、良率、OEE、工艺参数"""

import random


class LineState:
    """单条半导体产线的实时状态模拟。

    维护当前指标快照和基线参数，支持工艺漂移、随机波动和外部调整。
    """

    def __init__(
        self,
        name: str,
        base_output: float,
        base_yield: float,
        drift_rate: float = 0.0002,
        extra_params: dict | None = None,
    ):
        self.name = name
        self.base_output = base_output
        self.base_yield = base_yield
        self.drift_rate = drift_rate

        # 当前指标
        self.current_output = base_output
        self.current_yield = base_yield
        self.current_oee = 0.85

        # 工艺参数（可被Agent调整）
        self.params = extra_params or {}

        # 状态
        self.status = "running"  # running / warning / alarm / idle
        self._recovery_trend = 0.0  # 调整后的恢复趋势

    def tick(self, elapsed_hours: float,
             upstream_yields: list[float] | None = None) -> dict:
        """推进一帧（每秒调用），返回当前状态快照。

        Args:
            elapsed_hours: 累计运行小时数（用于漂移计算）
            upstream_yields: 上游产线的良率列表（用于下游联动）
        """
        # 1. 基础波动：正负5%随机噪声
        self.current_output = self.base_output * random.uniform(0.95, 1.05)
        self.current_yield = max(0.01, min(1.0,
            self.base_yield * random.uniform(0.98, 1.02)
        ))
        self.current_oee = min(1.0, max(0.01,
            0.85 + random.uniform(-0.07, 0.05)
        ))

        # 2. 工艺漂移：良率随时间下降（演示加速：系数x30，2-3分钟可见效）
        drift_loss = elapsed_hours * self.drift_rate * 30
        self.current_yield = max(0.01, self.current_yield - drift_loss)

        # 3. 恢复趋势（如果Agent做了调整）
        if self._recovery_trend != 0:
            self.current_yield = min(
                self.base_yield,
                self.current_yield + self._recovery_trend
            )
            # 恢复趋势逐渐衰减
            self._recovery_trend *= 0.95
            if abs(self._recovery_trend) < 0.0001:
                self._recovery_trend = 0.0

        # 4. 参数自然波动
        for key in self.params:
            if isinstance(self.params[key], (int, float)):
                self.params[key] *= random.uniform(0.99, 1.01)

        # 5. 上游联动：上游良率下降会影响当前产线的产出效率
        if upstream_yields:
            avg_upstream = sum(upstream_yields) / len(upstream_yields)
            self.current_output *= (0.8 + 0.2 * avg_upstream)

        # 6. 状态判定
        if self.current_yield < self.base_yield - 0.04:
            self.status = "alarm"
        elif self.current_yield < self.base_yield - 0.02:
            self.status = "warning"
        elif self.current_oee < 0.60:
            self.status = "alarm"
        else:
            self.status = "running"

        return self.snapshot()

    def snapshot(self) -> dict:
        """返回当前状态的快照字典"""
        return {
            "name": self.name,
            "output": round(self.current_output, 1),
            "yield_rate": round(self.current_yield, 4),
            "oee": round(self.current_oee, 4),
            "status": self.status,
            "params": dict(self.params),
        }

    def apply_adjustment(self, param: str, new_value: float):
        """响应Agent调整指令"""
        self.params[param] = new_value
        self._recovery_trend = 0.015  # 每帧恢复1.5%良率
