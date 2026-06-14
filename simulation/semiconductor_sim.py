"""半导体产线仿真核心 — 三条产线 + 异常事件注入 + 调整响应"""

import time
import random
import threading
from simulation.production_line import LineState


class SemiconductorSimulator:
    """半导体制造产线仿真引擎。

    模拟三条产线：光刻(Litho) → 刻蚀(Etch) → 测试(Test)
    支持：基线波动、工艺漂移、异常事件注入、上游→下游联动、Agent参数调整
    """

    def __init__(self):
        # 光刻线：基产120wph, 基良率96.5%, 慢漂移
        self.litho = LineState(
            name="光刻线 #L1",
            base_output=120.0,
            base_yield=0.965,
            drift_rate=0.0002,
            extra_params={
                "exposure_dose": 25.0,      # mJ/cm²
                "focus_offset": 12.5,       # nm
                "alignment_error": 0.8,     # nm
            },
        )

        # 刻蚀线：基产95wph, 基良率94.0%, 漂移略快
        self.etch = LineState(
            name="刻蚀线 #E1",
            base_output=95.0,
            base_yield=0.940,
            drift_rate=0.0003,
            extra_params={
                "rf_power": 500.0,          # W
                "chamber_pressure": 32.0,   # mTorr
                "etch_rate": 98.5,          # nm/min
            },
        )

        # 测试线：LineState用于基础参数，特有指标单独维护
        self.test = LineState(
            name="测试线 #T1",
            base_output=200.0,
            base_yield=0.0,  # 测试线不使用良率指标
            drift_rate=0.0,
            extra_params={
                "sampling_rate": 80.0,      # %
                "test_threshold": 5.0,      # 判定阈值
            },
        )

        # 测试线特有指标
        self.test_dppm = 450
        self.test_utilization = 0.77
        self.test_bin1 = 0.87   # 良品
        self.test_bin2 = 0.08   # 可修复
        self.test_bin3 = 0.05   # 报废

        # 运行状态
        self.elapsed_seconds = 0
        self._running = False
        self._thread = None

        # 日志
        self.adjustment_log: list[dict] = []   # Agent调整记录
        self.event_log: list[dict] = []        # 异常事件记录
        self.auto_check_log: list[dict] = []   # 自动检测记录

    def tick(self) -> dict:
        """推进一帧（每秒调用），返回当前完整快照。"""
        self.elapsed_seconds += 1
        elapsed_hours = self.elapsed_seconds / 3600.0

        # 推进各产线
        litho_data = self.litho.tick(elapsed_hours)
        etch_data = self.etch.tick(
            elapsed_hours,
            upstream_yields=[litho_data["yield_rate"]],
        )

        # 测试线：受上游光刻+刻蚀良率影响
        upstream_avg_yield = (
            litho_data["yield_rate"] + etch_data["yield_rate"]
        ) / 2
        self.test_dppm = int(
            250
            + (1 - litho_data["yield_rate"]) * 1500
            + (1 - etch_data["yield_rate"]) * 1200
            + random.randint(-20, 20)
        )
        self.test_utilization = min(0.99, max(0.5,
            0.77 + random.uniform(-0.05, 0.05)
        ))
        self.test_bin1 = max(0.01, min(0.99,
            0.88
            - (1 - upstream_avg_yield) * 0.4
            + random.uniform(-0.02, 0.02)
        ))
        self.test_bin2 = max(0.01, min(0.5,
            0.08 + random.uniform(-0.02, 0.02)
        ))
        self.test_bin3 = max(0.01, 1.0 - self.test_bin1 - self.test_bin2)

        # 测试线状态判定
        if self.test_dppm > 600:
            test_status = "alarm"
        elif self.test_dppm > 500:
            test_status = "warning"
        else:
            test_status = "running"

        test_data = {
            "name": "测试线 #T1",
            "throughput": round(self.test.base_output * random.uniform(0.93, 1.07), 1),
            "dppm": self.test_dppm,
            "utilization": round(self.test_utilization, 4),
            "status": test_status,
            "bin_distribution": {
                "bin1_good": round(self.test_bin1, 4),
                "bin2_repairable": round(self.test_bin2, 4),
                "bin3_scrap": round(self.test_bin3, 4),
            },
            "params": dict(self.test.params),
        }

        # 随机异常事件注入
        events = self._maybe_trigger_events()

        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_seconds": self.elapsed_seconds,
            "production_lines": {
                "litho": litho_data,
                "etch": etch_data,
                "test": test_data,
            },
            "events": events,
        }

    def _maybe_trigger_events(self) -> list[dict]:
        """按概率触发异常事件"""
        events = []
        seconds = self.elapsed_seconds

        # 事件1: 光刻胶老化 — 每30分钟(1800秒)概率检查
        if seconds % 1800 == 0 and seconds > 0 and random.random() < 0.7:
            self.litho.base_yield *= 0.96  # 基良率掉4%
            event = {
                "time": time.strftime("%H:%M:%S"),
                "type": "alarm",
                "line": "litho",
                "message": (
                    f"[告警] 光刻线良率异常下降 — 疑似光刻胶老化 "
                    f"(当前: {self.litho.current_yield*100:.1f}%)"
                ),
                "suggested_action": "曝光剂量补偿 +2 mJ/cm² 或安排换胶",
            }
            events.append(event)
            self.event_log.append(event)

        # 事件2: 刻蚀速率漂移 — 每45分钟
        if seconds % 2700 == 0 and seconds > 0 and random.random() < 0.6:
            direction = random.choice([-1, 1])
            drift_pct = 0.08 * direction
            old_rate = self.etch.params.get("etch_rate", 98.5)
            self.etch.params["etch_rate"] = old_rate * (1 + drift_pct)
            event = {
                "time": time.strftime("%H:%M:%S"),
                "type": "warning",
                "line": "etch",
                "message": (
                    f"[警告] 刻蚀速率漂移 {drift_pct*100:+.1f}% "
                    f"— 当前: {self.etch.params['etch_rate']:.1f} nm/min"
                ),
                "suggested_action": (
                    f"RF功率调整 {'+' if direction > 0 else '-'}50W 补偿"
                ),
            }
            events.append(event)
            self.event_log.append(event)

        # 事件3: 设备OEE突降 — 每60分钟
        if seconds % 3600 == 0 and seconds > 0 and random.random() < 0.5:
            target = random.choice([self.litho, self.etch])
            target.current_oee = random.uniform(0.45, 0.58)
            line_name = "litho" if target is self.litho else "etch"
            event = {
                "time": time.strftime("%H:%M:%S"),
                "type": "alarm",
                "line": line_name,
                "message": (
                    f"[告警] {target.name} OEE骤降至 "
                    f"{target.current_oee*100:.1f}% — 疑似待料或小停机频发"
                ),
                "suggested_action": "建议PM排程检查 + 调整WIP上限",
            }
            events.append(event)
            self.event_log.append(event)

        return events

    def apply_adjustment(self, line: str, param: str, value: float):
        """接收Agent调整指令，修改产线参数。

        Args:
            line: 产线标识 "litho" / "etch" / "test"
            param: 参数名
            value: 新值
        """
        target = {"litho": self.litho, "etch": self.etch, "test": self.test}.get(line)
        if target is None:
            return
        if param in target.params:
            target.apply_adjustment(param, value)

    def start(self):
        """启动仿真线程"""
        self._running = True

    def stop(self):
        """停止仿真线程"""
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def get_summary(self) -> dict:
        """返回简洁摘要（供自动检测使用）"""
        return {
            "litho": {
                "yield_rate": self.litho.current_yield,
                "oee": self.litho.current_oee,
                "status": self.litho.status,
            },
            "etch": {
                "yield_rate": self.etch.current_yield,
                "oee": self.etch.current_oee,
                "status": self.etch.status,
            },
            "test": {
                "dppm": self.test_dppm,
                "utilization": self.test_utilization,
                "status": "warning" if self.test_dppm > 600 else "running",
            },
        }
