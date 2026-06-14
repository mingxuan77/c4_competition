# 半导体产线智能监控与决策系统 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有跨域分布式多智能体协同调度系统从通用场景（房产/高考）转型为半导体产线智能监控与决策系统，新增仿真引擎、产线监控Worker、产线调整Worker、监控仪表盘Tab页、双模式自动检测调整机制。

**Architecture:** 在现有 Streamlit + LangGraph + Workers 三层架构上新增仿真数据层，形成四层架构。通过 st.session_state 共享数据总线连接 Tab1(对话) 和 Tab2(监控)，实现对话-监控联动。新增2个Worker(production_monitor, production_adjuster)，更新意图解析模板，保持原有Worker和调度逻辑不变。

**Tech Stack:** Python 3.11+, Streamlit 1.30+, LangGraph 0.2+, LangChain, DeepSeek API, pandas, altair, python-docx, openpyxl, fpdf2

**Spec:** `docs/superpowers/specs/2026-06-14-production-line-monitoring-design.md`

---

## File Structure

```
simulation/                          ← 新建目录
├── __init__.py                      ← 新建: 导出 SemiconductorSimulator
├── production_line.py               ← 新建: LineState 单条产线状态机
└── semiconductor_sim.py             ← 新建: SemiconductorSimulator 仿真核心

workers/
├── production_monitor.py            ← 新建: 产线监控 Worker
├── production_adjuster.py           ← 新建: 产线调整 Worker

meta_agent/
├── intent_parser.py                 ← 修改: 移除旧模板，新增产线模板和关键词
├── langgraph_engine.py              ← 修改: 注册新Worker+新task_type
├── chat_llm.py                      ← 修改: 更新is_workflow_request关键词

config.py                             ← 修改: 更新system_prompt+仿真配置

app.py                                ← 重构: 多Tab+仿真生命周期+Tab2仪表盘

requirements.txt                      ← 修改: 添加altair
```

---

### Task 1: 创建仿真引擎基础 — LineState 数据模型

**Files:**
- Create: `simulation/__init__.py`
- Create: `simulation/production_line.py`

- [ ] **Step 1: Create `simulation/__init__.py`**

```python
"""半导体产线仿真引擎 — 实时数据生成与参数调整响应"""

from simulation.semiconductor_sim import SemiconductorSimulator

__all__ = ["SemiconductorSimulator"]
```

- [ ] **Step 2: Create `simulation/production_line.py`**

```python
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

        # 2. 工艺漂移：良率随时间缓慢下降
        drift_loss = elapsed_hours * self.drift_rate
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
```

- [ ] **Step 3: Commit**

```bash
git add simulation/__init__.py simulation/production_line.py
git commit -m "feat: add simulation engine — LineState production line model"
```

---

### Task 2: 创建半导体仿真核心 — SemiconductorSimulator

**Files:**
- Create: `simulation/semiconductor_sim.py`

- [ ] **Step 1: Create `simulation/semiconductor_sim.py`**

```python
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

        # 测试线：吞吐200uph, 受上游良率影响
        self.test = LineState(
            name="测试线 #T1",
            base_output=200.0,
            base_yield=0.0,  # 测试线不用良率指标
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
            300
            + (1 - litho_data["yield_rate"]) * 3000
            + (1 - etch_data["yield_rate"]) * 2500
            + random.randint(-30, 30)
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

        test_data = {
            "name": "测试线 #T1",
            "throughput": round(self.test.base_output * random.uniform(0.93, 1.07), 1),
            "dppm": self.test_dppm,
            "utilization": round(self.test_utilization, 4),
            "status": "warning" if self.test_dppm > 600 else "running",
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
                "message": f"[告警] 光刻线良率异常下降 — 疑似光刻胶老化 (当前: {self.litho.current_yield*100:.1f}%)",
                "suggested_action": "曝光剂量补偿 +2 mJ/cm² 或安排换胶",
            }
            events.append(event)
            self.event_log.append(event)

        # 事件2: 刻蚀速率漂移 — 每45分钟
        if seconds % 2700 == 0 and seconds > 0 and random.random() < 0.6:
            direction = random.choice([-1, 1])
            drift_pct = 0.08 * direction
            self.etch.params["etch_rate"] *= (1 + drift_pct)
            event = {
                "time": time.strftime("%H:%M:%S"),
                "type": "warning",
                "line": "etch",
                "message": f"[警告] 刻蚀速率漂移 {drift_pct*100:+.1f}% — 当前: {self.etch.params['etch_rate']:.1f} nm/min",
                "suggested_action": f"RF功率调整 {'+' if direction > 0 else '-'}50W 补偿",
            }
            events.append(event)
            self.event_log.append(event)

        # 事件3: 设备OEE突降 — 每60分钟
        if seconds % 3600 == 0 and seconds > 0 and random.random() < 0.5:
            target = random.choice([self.litho, self.etch])
            target.current_oee = random.uniform(0.45, 0.58)
            event = {
                "time": time.strftime("%H:%M:%S"),
                "type": "alarm",
                "line": "litho" if target is self.litho else "etch",
                "message": f"[告警] {target.name} OEE骤降至 {target.current_oee*100:.1f}% — 疑似待料或小停机频发",
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
        old = target.params.get(param)
        if old is not None:
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
```

- [ ] **Step 2: Verify imports work**

```bash
python -c "from simulation.semiconductor_sim import SemiconductorSimulator; sim = SemiconductorSimulator(); frame = sim.tick(); print(frame['production_lines']['litho']['name'])"
```
Expected: `光刻线 #L1`

- [ ] **Step 3: Commit**

```bash
git add simulation/semiconductor_sim.py
git commit -m "feat: add SemiconductorSimulator — 3-line production simulation with event injection"
```

---

### Task 3: 创建产线监控 Worker

**Files:**
- Create: `workers/production_monitor.py`

- [ ] **Step 1: Create `workers/production_monitor.py`**

```python
"""产线监控 Worker — 从仿真引擎读取实时数据，生成结构化诊断摘要"""

from workers.base_worker import BaseWorker


class ProductionMonitorWorker(BaseWorker):
    """产线监控Worker。

    读取仿真数据快照 + 近N帧历史，生成结构化摘要，
    调用LLM做初步诊断（如果LLM可用）。
    """

    def __init__(self):
        super().__init__("ProductionMonitor")

    def execute(self, task: dict) -> dict:
        desc = task.get("description", "")
        params = task.get("params", {})

        # 从注入的参数中读取仿真数据
        sim_snapshot = params.get("simulation_snapshot", {})
        sim_history = params.get("simulation_history", [])
        lines_data = sim_snapshot.get("production_lines", {})

        # 构建结构化文本摘要
        summary_parts = ["## 半导体产线实时状态\n"]
        for line_id, data in lines_data.items():
            name = data.get("name", line_id)
            status = data.get("status", "unknown")
            status_icon = {
                "running": "✅",
                "warning": "⚠️",
                "alarm": "🚨",
                "idle": "⏸️",
            }.get(status, "❓")

            summary_parts.append(f"### {status_icon} {name}")
            if line_id == "test":
                summary_parts.append(
                    f"- 吞吐量: {data.get('throughput', '-')} units/h\n"
                    f"- DPPM: {data.get('dppm', '-')}\n"
                    f"- 设备利用率: {data.get('utilization', 0)*100:.1f}%\n"
                    f"- Bin分布: 良品{data.get('bin_distribution',{}).get('bin1_good',0)*100:.1f}%"
                    f" / 可修{data.get('bin_distribution',{}).get('bin2_repairable',0)*100:.1f}%"
                    f" / 报废{data.get('bin_distribution',{}).get('bin3_scrap',0)*100:.1f}%\n"
                )
            else:
                summary_parts.append(
                    f"- 产出: {data.get('output', '-')} wph\n"
                    f"- 良率: {data.get('yield_rate', 0)*100:.1f}%\n"
                    f"- OEE: {data.get('oee', 0)*100:.1f}%\n"
                )

            # 工艺参数
            params_data = data.get("params", {})
            if params_data:
                summary_parts.append("- 工艺参数: ")
                param_strs = [
                    f"{k}={v:.1f}" if isinstance(v, float) else f"{k}={v}"
                    for k, v in params_data.items()
                ]
                summary_parts.append(", ".join(param_strs))
                summary_parts.append("\n")

        # 异常检测
        alerts = self._detect_alerts(lines_data)

        # 趋势分析（如果有历史数据）
        trend_summary = ""
        if sim_history and len(sim_history) >= 10:
            trend_summary = self._analyze_trends(sim_history)

        user_prompt = "".join(summary_parts)
        if trend_summary:
            user_prompt += f"\n\n## 趋势分析\n{trend_summary}"
        if alerts:
            user_prompt += f"\n\n## 异常告警\n" + "\n".join(f"- ⚠️ {a}" for a in alerts)

        # 尝试 LLM 诊断
        llm_output = self._call_llm(
            system_prompt=(
                "你是半导体产线监控专家。请根据产线实时数据给出初步诊断。"
                "要求：\n"
                "1. 识别每条产线的健康状态（正常/需关注/严重）\n"
                "2. 对异常指标给出可能的根因推断\n"
                "3. 评估是否需要人工干预（紧急/建议观察/无需）\n"
                "4. 输出简洁专业，500-1000字"
            ),
            user_prompt=user_prompt,
        )

        return {
            "output": llm_output or user_prompt,
            "raw_metrics": {
                line_id: {
                    "yield": data.get("yield_rate"),
                    "oee": data.get("oee"),
                    "output": data.get("output"),
                    "status": data.get("status"),
                }
                for line_id, data in lines_data.items()
            },
            "alerts": alerts,
        }

    def _detect_alerts(self, lines_data: dict) -> list[str]:
        """阈值检测"""
        alerts = []
        for line_id, data in lines_data.items():
            if line_id == "test":
                dppm = data.get("dppm", 0)
                if dppm > 600:
                    alerts.append(
                        f"测试线 DPPM 超标 ({dppm})，阈值600"
                    )
                if data.get("utilization", 0) > 0.95:
                    alerts.append(
                        f"测试线利用率过高 ({data['utilization']*100:.1f}%)，存在堆积风险"
                    )
            else:
                y = data.get("yield_rate", 1)
                if y < 0.90:
                    alerts.append(
                        f"{data.get('name', line_id)} 良率严重偏低 ({y*100:.1f}%)"
                    )
                elif y < 0.94:
                    alerts.append(
                        f"{data.get('name', line_id)} 良率偏低 ({y*100:.1f}%)"
                    )
                oee = data.get("oee", 1)
                if oee < 0.60:
                    alerts.append(
                        f"{data.get('name', line_id)} OEE告警 ({oee*100:.1f}%)"
                    )
        return alerts

    def _analyze_trends(self, history: list[dict]) -> str:
        """分析最近N帧数据的趋势"""
        if not history:
            return ""

        parts = []
        # 取最近10帧和最早1帧对比
        recent = history[-10:]
        first = history[0]
        last = history[-1]

        for line_id in ["litho", "etch"]:
            first_yield = (
                first.get("production_lines", {})
                .get(line_id, {})
                .get("yield_rate", 0)
            )
            last_yield = (
                last.get("production_lines", {})
                .get(line_id, {})
                .get("yield_rate", 0)
            )
            delta = (last_yield - first_yield) * 100
            if abs(delta) > 1:
                direction = "上升" if delta > 0 else "下降"
                parts.append(
                    f"- {first.get('production_lines', {}).get(line_id, {}).get('name', line_id)}: "
                    f"良率{direction} {abs(delta):.2f}个百分点"
                )

        return "\n".join(parts) if parts else "趋势正常，无明显异常变化"
```

- [ ] **Step 2: Verify imports**

```bash
python -c "from workers.production_monitor import ProductionMonitorWorker; w = ProductionMonitorWorker(); print(w.name)"
```
Expected: `ProductionMonitor`

- [ ] **Step 3: Commit**

```bash
git add workers/production_monitor.py
git commit -m "feat: add ProductionMonitorWorker — read simulation data and generate diagnosis"
```

---

### Task 4: 创建产线调整 Worker

**Files:**
- Create: `workers/production_adjuster.py`

- [ ] **Step 1: Create `workers/production_adjuster.py`**

```python
"""产线调整 Worker — 计算工艺参数调整量并写入仿真器"""

import json
import time
from workers.base_worker import BaseWorker


class ProductionAdjusterWorker(BaseWorker):
    """产线调整Worker。

    分析上游监控/诊断结果，调用LLM计算最优调整方案，
    通过仿真引擎接口执行参数调整。
    """

    def __init__(self):
        super().__init__("ProductionAdjuster")

    def execute(self, task: dict) -> dict:
        desc = task.get("description", "")
        params = task.get("params", {})

        # 收集上游数据
        upstream = params.get("upstream_results", {})
        sim_snapshot = params.get("simulation_snapshot", {})
        target_line = params.get("target_line", "auto")

        # 从上游提取告警
        alerts = []
        upstream_outputs = []
        for uid, r in upstream.items():
            if isinstance(r, dict):
                alerts.extend(r.get("alerts", []))
                output = r.get("output", "")
                if output:
                    upstream_outputs.append(f"[{uid}]: {output[:800]}")

        # 构建当前状态文本
        lines = sim_snapshot.get("production_lines", {})
        current_state_text = ""
        for line_id, data in lines.items():
            current_state_text += (
                f"{data.get('name', line_id)}:\n"
                f"  状态={data.get('status')}, "
                f"良率={data.get('yield_rate', 0)*100:.1f}%, "
                f"OEE={data.get('oee', 0)*100:.1f}%, "
                f"参数={data.get('params', {})}\n"
            )
            if line_id == "test":
                current_state_text += (
                    f"  DPPM={data.get('dppm')}, "
                    f"利用率={data.get('utilization', 0)*100:.1f}%\n"
                )

        # 构建prompt
        user_prompt = (
            f"## 当前产线状态\n{current_state_text}\n"
            f"## 异常告警\n" + "\n".join(f"- {a}" for a in alerts) + "\n"
            f"## 上游诊断\n" + "\n".join(upstream_outputs) + "\n"
            f"## 目标产线: {target_line}\n\n"
            f"请给出具体的工艺参数调整方案。"
        )

        llm_result = self._call_llm(
            system_prompt=(
                "你是半导体工艺工程师。根据产线异常数据，给出具体可量化的工艺参数调整方案。\n\n"
                "可调参数范围：\n"
                "- 光刻线(litho): exposure_dose (20-30 mJ/cm²), focus_offset (0-50 nm)\n"
                "- 刻蚀线(etch): rf_power (400-600 W), chamber_pressure (20-50 mTorr)\n"
                "- 测试线(test): sampling_rate (50-100 %)\n\n"
                "规则：\n"
                "1. 良率偏低 → 优先调整曝光剂量(光刻)或RF功率(刻蚀)\n"
                "2. 每次调整幅度不宜过大（曝光剂量±2以内, RF功率±50以内）\n"
                "3. 同时调整最多2个参数\n"
                "4. 每个调整给出理由\n\n"
                "输出严格JSON格式（不要markdown标记）：\n"
                '{"adjustments": [{"line": "litho", "param": "exposure_dose", '
                '"old_value": 25.0, "new_value": 26.5, "reason": "补偿光刻胶老化"}], '
                '"summary": "一句话总结调整方案"}'
            ),
            user_prompt=user_prompt,
        )

        # 解析调整方案
        parsed = self._parse_adjustment_json(llm_result or "{}")
        adjustments = parsed.get("adjustments", [])

        # 注入仿真器
        applied = self._apply_to_simulator(adjustments)

        # 构建输出报告
        result = {"worker": self.name, "applied_adjustments": applied}

        if applied:
            adjust_text = "\n".join(
                f"- {a['line']}.{a['param']}: {a['old_value']} → {a['new_value']} ({a['reason']})"
                for a in applied
            )
            result["output"] = (
                f"## 🔧 产线工艺参数调整执行完毕\n\n"
                f"已执行 {len(applied)} 项调整：\n\n{adjust_text}\n\n"
                f"预计效果：良率将在2分钟内开始回升"
            )
        else:
            result["output"] = (
                f"[产线调整] 当前无需调整。所有产线指标在正常范围内。"
            )

        return result

    def _parse_adjustment_json(self, text: str) -> dict:
        """从LLM输出中提取JSON"""
        # 去除可能的markdown代码块标记
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 回退：尝试寻找JSON片段
            import re
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return {}

    def _apply_to_simulator(self, adjustments: list) -> list:
        """将调整指令写入仿真引擎（通过st.session_state）"""
        import streamlit as st

        applied = []
        sim_engine = st.session_state.get("simulation_engine")
        if sim_engine is None:
            return applied

        for adj in adjustments:
            line = adj.get("line", "")
            param = adj.get("param", "")
            new_val = adj.get("new_value")
            old_val = adj.get("old_value")
            reason = adj.get("reason", "")

            if not line or not param or new_val is None:
                continue

            # 实际调用仿真器接口
            sim_engine.apply_adjustment(line, param, new_val)

            record = {
                "time": time.strftime("%H:%M:%S"),
                "line": line,
                "param": param,
                "old_value": old_val,
                "new_value": new_val,
                "reason": reason,
            }
            applied.append(record)

            # 写入仿真器调整日志（Tab2会读取）
            sim_engine.adjustment_log.append({
                "time": record["time"],
                "agent": "产能调整Agent",
                "type": "manual",
                "line": line,
                "param": param,
                "old_value": old_val,
                "new_value": new_val,
                "reason": reason,
            })

        return applied
```

- [ ] **Step 2: Verify imports**

```bash
python -c "from workers.production_adjuster import ProductionAdjusterWorker; w = ProductionAdjusterWorker(); print(w.name)"
```
Expected: `ProductionAdjuster`

- [ ] **Step 3: Commit**

```bash
git add workers/production_adjuster.py
git commit -m "feat: add ProductionAdjusterWorker — compute and apply line parameter adjustments"
```

---

### Task 5: 更新意图解析器 — 新模板 + 新关键词

**Files:**
- Modify: `meta_agent/intent_parser.py`

- [ ] **Step 1: Remove old irrelevant templates**

Read `meta_agent/intent_parser.py` and delete these entries from `PRESET_PIPELINES`:
- `"房地产投资分析"` (lines ~97-108)
- `"高考志愿填报"` (lines ~150-159)

Keep: `"数据中心安全运维"`, `"数据分析"`, `"智能路由"`, `"安全审计"`, `"数据库迁移"`.

- [ ] **Step 2: Add new semiconductor production line templates**

After the remaining `PRESET_PIPELINES` entries, add:

```python
    "产线状态检测": {
        "intent": "半导体产线状态检测与异常诊断",
        "tasks": [
            {"task_id": "A", "type": "production_monitor",
             "description": "读取光刻/刻蚀/测试三条产线当前运行指标和历史趋势数据"},
            {"task_id": "B", "type": "data_processing",
             "description": "分析异常趋势：良率下降斜率、OEE波动模式、DPPM变化率"},
            {"task_id": "C", "type": "strategy",
             "description": "综合诊断报告：识别异常产线、推断根因、给出处理建议和优先级"},
            {"task_id": "D", "type": "report_export",
             "description": "导出产线检测报告（Word/Excel/PDF格式）"},
        ],
        "dependencies": {"B": ["A"], "C": ["B"], "D": ["C"]},
    },
    "产线自动调整": {
        "intent": "半导体产线工艺参数智能调整",
        "tasks": [
            {"task_id": "A", "type": "production_monitor",
             "description": "拉取目标产线近30分钟历史数据和当前工艺参数"},
            {"task_id": "B", "type": "ml_prediction",
             "description": "预测当前漂移趋势下未来15分钟的良率变化"},
            {"task_id": "C", "type": "production_adjuster",
             "description": "计算最优工艺参数调整量并写入仿真器执行"},
            {"task_id": "D", "type": "strategy",
             "description": "调整效果评估：预期恢复时间、风险评估、后续监控建议"},
            {"task_id": "E", "type": "report_export",
             "description": "导出调整报告（Word/Excel/PDF格式）"},
        ],
        "dependencies": {"B": ["A"], "C": ["B"], "D": ["C"], "E": ["D"]},
    },
    "产线综合分析": {
        "intent": "半导体产线综合运行分析与瓶颈诊断",
        "tasks": [
            {"task_id": "A", "type": "production_monitor",
             "description": "全量采集三条产线运行数据、事件日志和调整历史"},
            {"task_id": "B", "type": "data_processing",
             "description": "数据清洗与相关性分析：良率-参数关联、OEE瓶颈识别"},
            {"task_id": "C", "type": "ml_prediction",
             "description": "基于历史趋势预测未来2小时良率和产能走势"},
            {"task_id": "D", "type": "strategy",
             "description": "综合决策报告：瓶颈排序、维护优先级、产能优化建议"},
            {"task_id": "E", "type": "report_export",
             "description": "导出综合分析报告（Word/Excel/PDF格式）"},
        ],
        "dependencies": {"B": ["A"], "C": ["B"], "D": ["C"], "E": ["D"]},
    },
    "设备故障诊断": {
        "intent": "半导体设备故障诊断与维护建议",
        "tasks": [
            {"task_id": "A", "type": "production_monitor",
             "description": "读取OEE异常产线的详细设备状态和故障日志"},
            {"task_id": "B", "type": "algorithm",
             "description": "故障模式匹配：比对已知故障特征库，识别可能根因"},
            {"task_id": "C", "type": "strategy",
             "description": "输出故障诊断报告：根因排序、修复建议、预计恢复时间"},
            {"task_id": "D", "type": "report_export",
             "description": "导出故障诊断报告（Word/Excel/PDF格式）"},
        ],
        "dependencies": {"B": ["A"], "C": ["B"], "D": ["C"]},
    },
```

- [ ] **Step 3: Add new task type keywords to TASK_TYPES dict**

After the `"http_request"` entry, add:

```python
    "production_monitor": {
        "keywords": ["检测", "监控", "产线", "良率", "产能", "OEE", "状态",
                     "光刻", "刻蚀", "测试", "异常", "DPPM"],
        "worker": "production_monitor",
        "label": "产线监控",
        "description_template": "读取产线实时数据与历史趋势",
    },
    "production_adjuster": {
        "keywords": ["调整", "补偿", "修改参数", "优化工艺", "调参",
                     "曝光剂量", "RF功率", "腔室压力"],
        "worker": "production_adjuster",
        "label": "产线调整",
        "description_template": "计算并执行产线工艺参数调整",
    },
```

- [ ] **Step 4: Add preset triggers for new templates**

In `preset_triggers` dict (inside `_parse_with_rules`), add:

```python
    "产线状态检测": ["检测", "产线", "良率", "异常", "状态", "监控"],
    "产线自动调整": ["调整", "补偿", "修改参数", "优化", "曝光", "RF", "功率"],
    "产线综合分析": ["综合", "全面分析", "瓶颈", "报告"],
    "设备故障诊断": ["故障", "宕机", "OEE", "停机", "维修"],
```

- [ ] **Step 5: Verify rule matching works**

```bash
python -c "
from meta_agent.intent_parser import IntentParser
p = IntentParser()
r = p._parse_with_rules('光刻线良率异常，帮我检测一下三条产线')
print(r['intent'])
print([t['type'] for t in r['tasks']])
"
```
Expected: intent contains "产线状态检测" and task types include `production_monitor`.

- [ ] **Step 6: Commit**

```bash
git add meta_agent/intent_parser.py
git commit -m "feat: update intent parser — add semiconductor production line templates, remove obsolete templates"
```

---

### Task 6: 注册新Worker到LangGraph调度引擎

**Files:**
- Modify: `meta_agent/langgraph_engine.py`

- [ ] **Step 1: Add new task type mappings**

In `TASK_TYPE_MAP` (around line 55), after `"report_export"` entry, add:

```python
    "production_monitor":  ("production_monitor",  "产线监控", "📡"),
    "production_adjuster": ("production_adjuster", "产线调整", "🔧"),
```

- [ ] **Step 2: Register new workers in _get_workers cache**

Import the new workers at the top of `_get_workers()` function (around line 71), after existing imports:

```python
        from workers.production_monitor import ProductionMonitorWorker
        from workers.production_adjuster import ProductionAdjusterWorker
```

In `_workers_cache` dict (around line 85), after `"report_exporter"` entry:

```python
            "production_monitor": ProductionMonitorWorker(),
            "production_adjuster": ProductionAdjusterWorker(),
```

- [ ] **Step 3: Update LangChain intent parser schema**

In `parse_intent_with_langchain`, update the schema's `enum` list to include new types. In the `schema` dict (around line 270), change `"enum": list(TASK_TYPE_MAP.keys())` — this already dynamically picks up new types since we added them to TASK_TYPE_MAP. Verify by checking it references `TASK_TYPE_MAP`.

- [ ] **Step 4: Update the system prompt for intent parsing**

In the `system_prompt` variable of `parse_intent_with_langchain` (around line 283), add new task types to the list:

```
- production_monitor: 产线监控(读取仿真数据/检测异常/趋势分析)
- production_adjuster: 产线调整(计算调整量/执行工艺参数修改)
```

- [ ] **Step 5: Verify worker registration**

```bash
python -c "
from meta_agent.langgraph_engine import TASK_TYPE_MAP, _get_workers
print('production_monitor' in TASK_TYPE_MAP)
print('production_adjuster' in TASK_TYPE_MAP)
workers = _get_workers()
print('production_monitor' in workers)
print('production_adjuster' in workers)
"
```
Expected: All four print `True`.

- [ ] **Step 6: Commit**

```bash
git add meta_agent/langgraph_engine.py
git commit -m "feat: register ProductionMonitor and ProductionAdjuster workers in LangGraph engine"
```

---

### Task 7: 更新配置与对话系统

**Files:**
- Modify: `config.py`
- Modify: `meta_agent/chat_llm.py`

- [ ] **Step 1: Update CHAT_CONFIG system_prompt in `config.py`**

Replace the `system_prompt` (around line 23) with:

```python
    "system_prompt": """你是"半导体产线智能监控与决策系统"的智能助手，基于 Internet of Agents 架构。

你的核心能力：
1. **产线状态检测**：实时监控光刻、刻蚀、测试三条产线的运行指标（良率、产能、OEE、DPPM）
2. **异常诊断**：自动识别良率波动、设备OEE告警、工艺参数漂移等异常
3. **智能调整**：计算最优工艺参数（曝光剂量、RF功率、腔室压力等）并自动执行调整
4. **多Agent协同**：管理12类专业Agent，从监控→分析→调整→策略→报告全流程自动化

你可以帮用户：
- 检测产线状态："检查三条产线现在的运行状态"
- 分析异常："光刻线良率持续下降，分析原因"
- 执行调整："把光刻线曝光剂量补偿+2"
- 综合诊断："对全产线做综合分析，找出良率瓶颈"
- 生成报告："生成本周产线运行报告"

当用户描述一个需要多步骤分析的复杂任务时，系统会自动调度多Agent协同工作。
对于简单问答，你会直接以AI助手身份回复。

请用中文回复，保持专业、清晰、有帮助。""",
```

- [ ] **Step 2: Add simulation config to `config.py`**

At the end of `config.py`, add:

```python
# 产线仿真配置
SIMULATION_CONFIG = {
    "tick_interval_seconds": 1,     # 仿真帧间隔
    "history_max_frames": 300,      # 最大保留历史帧数（5分钟）
    "auto_check_default_interval": 300,  # 自动检测默认间隔（秒）
    "auto_check_intervals": [180, 300, 600],  # 可选间隔: 3/5/10分钟
    "yield_warning_threshold": 0.03,  # 良率警告阈值（下降3%触发）
    "yield_alarm_threshold": 0.05,   # 良率告警阈值（下降5%触发）
    "oee_alarm_threshold": 0.60,     # OEE告警阈值
    "dppm_alarm_threshold": 600,     # DPPM告警阈值
}
```

- [ ] **Step 3: Update workflow detection keywords in `chat_llm.py`**

In `is_workflow_request()` function, add to `workflow_keywords`:

```python
    "检测", "产线", "良率", "产能", "OEE", "DPPM",
    "光刻", "刻蚀", "测试", "调整", "补偿", "漂移", "故障",
```

- [ ] **Step 4: Commit**

```bash
git add config.py meta_agent/chat_llm.py
git commit -m "feat: update config and chat for semiconductor production line scenario"
```

---

### Task 8: 重构 app.py — 多Tab架构 + 仿真生命周期

**Files:**
- Modify: `app.py`

This is the largest task. We'll refactor app.py to support multi-tab layout and simulation lifecycle.

- [ ] **Step 1: Add new imports at top of `app.py`**

After existing imports, add:

```python
import threading
import time
import pandas as pd

from simulation.semiconductor_sim import SemiconductorSimulator
from config import SIMULATION_CONFIG
```

- [ ] **Step 2: Add simulation session state variables**

In the `DEFAULTS` dict (around line 219), add:

```python
    "simulation_engine": None,
    "simulation_active": False,
    "simulation_data": {},
    "simulation_history": [],
    "simulation_log": [],
    "auto_check_enabled": True,
    "auto_check_interval": SIMULATION_CONFIG["auto_check_default_interval"],
    "current_tab": "chat",
```

- [ ] **Step 3: Replace sidebar example tasks**

Replace the `examples` list (around line 508) with:

```python
    examples = [
        ("🔍 产线检测", "全面检测三条产线的运行状态，分析良率和产能异常"),
        ("🔧 自动调整", "光刻线良率持续下降，分析原因并自动调整工艺参数"),
        ("📊 综合分析", "对刻蚀线和测试线进行联合分析，找出良率瓶颈"),
        ("⚡ 故障诊断", "设备OEE突然下降，排查是待料问题还是设备故障"),
        ("📝 生成报告", "生成本周产线运行综合报告，包含趋势和建议"),
    ]
```

- [ ] **Step 4: Replace welcome message**

Replace the welcome message (around line 547) with:

```python
            st.markdown("""
            <div style="text-align:center; padding:40px 20px; color:#667788;">
                <p style="font-size:3rem; margin-bottom:10px;">🏭</p>
                <p style="font-size:1.2rem; font-weight:600; color:#4a4ae8;">半导体产线智能监控与决策系统</p>
                <p style="font-size:0.9rem;">基于多Agent协同的产线状态检测 · 异常诊断 · 工艺调整 · 决策报告</p>
                <p style="font-size:0.8rem; color:#8899aa;">支持：光刻线 · 刻蚀线 · 测试线 | 实时监控 + 智能分析 + 自动调整</p>
            </div>
            """, unsafe_allow_html=True)
```

- [ ] **Step 5: Replace single-page layout with multi-tab**

Replace the `col_main, col_right = st.columns([2.2, 1], gap="medium")` line and everything after it with a tab structure.

Instead of the current `col_main` / `col_right` layout that starts at line 534, wrap the entire block (from line 534 to end of file) in:

```python
# ─── Tab 切换 ────────────────────────────────────────────
tab1, tab2 = st.tabs(["💬 智能对话", "📊 产线监控"])

# ═══════════════════════════════════════════════════════════
# Tab 1: 智能对话
# ═══════════════════════════════════════════════════════════
with tab1:
    col_main, col_right = st.columns([2.2, 1], gap="medium")
    # ... 保留现有所有 Tab1 内容（标题、聊天、输入、右侧面板） ...
```

Important: The existing content from line 534 onwards should be placed inside `with tab1:` block, wrapping the existing col_main/col_right layout. The entire existing logic (chat, workflow execution, sidebar, etc.) remains unchanged except for the items already modified in steps 3-4.

- [ ] **Step 6: Add simulation lifecycle functions**

Before the tab structure, add these helper functions:

```python
# ─── 仿真生命周期管理 ───────────────────────────────────

def start_simulation():
    """启动产线仿真引擎"""
    if st.session_state.simulation_engine is None:
        st.session_state.simulation_engine = SemiconductorSimulator()

    sim = st.session_state.simulation_engine
    if sim.is_running():
        return

    sim.start()
    st.session_state.simulation_active = True

    def _sim_loop():
        """仿真主循环 — 在后台线程中运行"""
        while st.session_state.simulation_active and sim.is_running():
            frame = sim.tick()
            st.session_state.simulation_data = frame
            st.session_state.simulation_history.append(frame)
            # 只保留最近 history_max_frames 帧
            max_frames = SIMULATION_CONFIG["history_max_frames"]
            if len(st.session_state.simulation_history) > max_frames:
                st.session_state.simulation_history = (
                    st.session_state.simulation_history[-max_frames:]
                )
            time.sleep(SIMULATION_CONFIG["tick_interval_seconds"])

    thread = threading.Thread(target=_sim_loop, daemon=True)
    thread.start()


def stop_simulation():
    """停止产线仿真引擎"""
    if st.session_state.simulation_engine:
        st.session_state.simulation_engine.stop()
    st.session_state.simulation_active = False


def toggle_simulation():
    """切换仿真启停状态"""
    if st.session_state.simulation_active:
        stop_simulation()
    else:
        start_simulation()
    st.rerun()
```

- [ ] **Step 7: Inject simulation data into workflow execution**

In the `execute_workflow` function (around line 419), after the function signature, add simulation data injection to each task's params before LangGraph execution. Find the line `engine_result = run_with_langgraph(tasks, user_input)` (around line 461) and modify the task preparation before it:

```python
    # 步骤2: LangGraph 并行调度执行
    # 注入仿真数据到任务参数中
    for task in tasks:
        if task.get("task_type") in ("production_monitor", "production_adjuster"):
            task.setdefault("params", {})
            task["params"]["simulation_snapshot"] = st.session_state.get("simulation_data", {})
            task["params"]["simulation_history"] = st.session_state.get("simulation_history", [])

    from meta_agent.langgraph_engine import run_with_langgraph
    if status_callback:
        status_callback("🚀 Agent调度执行中...", 70, logs, intent_result, tasks)
    engine_result = run_with_langgraph(tasks, user_input)
```

- [ ] **Step 8: Update sidebar Agent list**

Replace the agents list (around line 855) with the updated 12-agent list:

```python
        agents = [
            ("📡", "产线监控", "实时读取产线运行数据"),
            ("🔧", "产线调整", "计算并执行工艺参数调整"),
            ("🔍", "数据检索", "多源数据搜索获取"),
            ("🧹", "数据处理", "清洗/ETL/趋势分析"),
            ("🤖", "机器学习", "预测/分类/回归"),
            ("⚙️", "算法优化", "路径/组合/调度"),
            ("🛡️", "安全分析", "漏洞扫描/风险评估"),
            ("🌐", "网络监控", "拓扑/流量/异常"),
            ("🗄️", "数据库", "查询优化/迁移"),
            ("💻", "代码执行", "沙箱安全执行"),
            ("📊", "策略输出", "综合报告/建议"),
            ("📄", "报告导出", "Word/Excel/PDF文件"),
        ]
```

- [ ] **Step 9: Commit**

```bash
git add app.py
git commit -m "feat: refactor app.py — multi-tab layout, simulation lifecycle, semiconductor scenario"
```

---

### Task 9: 构建 Tab2 产线监控仪表盘

**Files:**
- Modify: `app.py` (add Tab2 content)

- [ ] **Step 1: Add Tab2 rendering function**

Add this function before the tab structure:

```python
def render_monitoring_dashboard():
    """渲染 Tab2: 产线监控仪表盘"""

    # === 控制栏 ===
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([0.3, 0.25, 0.45])
    with ctrl_col1:
        sim_active = st.session_state.simulation_active
        btn_label = "⏸️ 停止仿真" if sim_active else "▶️ 启动仿真"
        if st.button(btn_label, use_container_width=True, type="primary" if not sim_active else "secondary"):
            toggle_simulation()
    with ctrl_col2:
        auto_enabled = st.toggle(
            "🔁 自动检测调整",
            value=st.session_state.auto_check_enabled,
            help="开启后每N分钟自动检测产线异常并执行轻量级调整"
        )
        st.session_state.auto_check_enabled = auto_enabled
        interval = st.selectbox(
            "间隔(分钟)",
            [3, 5, 10],
            index=1,
            key="auto_interval_selector",
            label_visibility="collapsed",
        )
        st.session_state.auto_check_interval = interval * 60
    with ctrl_col3:
        if st.session_state.simulation_engine:
            elapsed = st.session_state.simulation_engine.elapsed_seconds
            h = elapsed // 3600
            m = (elapsed % 3600) // 60
            s = elapsed % 60
            st.metric("运行时长", f"{h:02d}:{m:02d}:{s:02d}")
        else:
            st.metric("运行时长", "--:--:--")

    st.markdown("---")

    # === 三条产线指标卡片 ===
    sim_data = st.session_state.simulation_data
    if sim_data and sim_data.get("production_lines"):
        lines = sim_data["production_lines"]
        card_col_l, card_col_e, card_col_t, card_col_log = st.columns(
            [0.22, 0.22, 0.22, 0.34]
        )

        with card_col_l:
            _render_line_card("litho", lines.get("litho", {}))
        with card_col_e:
            _render_line_card("etch", lines.get("etch", {}))
        with card_col_t:
            _render_test_card(lines.get("test", {}))
        with card_col_log:
            _render_adjustment_log()

        st.markdown("---")

        # === 良率趋势图 ===
        st.subheader("📈 良率趋势")
        _render_yield_chart()

        # === 产出台账 ===
        st.subheader("📊 产出台账")
        _render_output_chart()

        # === 事件时间线 ===
        st.subheader("⚡ 事件时间线")
        _render_event_timeline()
    else:
        st.markdown("""
        <div style="text-align:center; padding:60px 20px; color:#8899aa;">
            <p style="font-size:3rem;">🏭</p>
            <p style="font-size:1.1rem;">产线仿真未启动</p>
            <p style="font-size:0.85rem;">点击上方「启动仿真」按钮开始监控</p>
        </div>
        """, unsafe_allow_html=True)
```

- [ ] **Step 2: Add card rendering helper functions**

```python
def _render_line_card(line_id: str, data: dict):
    """渲染光刻/刻蚀产线指标卡片"""
    if not data:
        st.caption("无数据")
        return

    name = data.get("name", line_id)
    status = data.get("status", "running")
    color = {
        "running": "#00a878",
        "warning": "#e8a020",
        "alarm": "#e04040",
        "idle": "#8899aa",
    }.get(status, "#8899aa")

    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #e0e4ea;'
        f'border-left:4px solid {color};border-radius:8px;'
        f'padding:10px 12px;margin:2px 0;">'
        f'<div style="font-weight:700;font-size:0.9rem;color:#1a1a30;">{name}</div>'
        f'<div style="color:{color};font-size:0.78rem;font-weight:600;">'
        f'{"✅ 正常" if status=="running" else "⚠️ 警告" if status=="warning" else "🚨 告警" if status=="alarm" else "⏸️ 空闲"}'
        f'</div>',
        unsafe_allow_html=True,
    )

    output = data.get("output", 0)
    yield_rate = data.get("yield_rate", 0) * 100
    oee = data.get("oee", 0) * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("产出(wph)", f"{output:.0f}")
    c2.metric("良率", f"{yield_rate:.1f}%")
    c3.metric("OEE", f"{oee:.1f}%")

    # 工艺参数
    params = data.get("params", {})
    if params:
        with st.expander("工艺参数", expanded=False):
            for k, v in params.items():
                st.caption(f"{k}: {v:.1f}")

    st.markdown("</div>", unsafe_allow_html=True)


def _render_test_card(data: dict):
    """渲染测试线指标卡片"""
    if not data:
        st.caption("无数据")
        return

    dppm_val = data.get("dppm", 0)
    status = "alarm" if dppm_val > 600 else "warning" if dppm_val > 500 else "running"
    color = {"running": "#00a878", "warning": "#e8a020", "alarm": "#e04040"}.get(status, "#8899aa")

    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #e0e4ea;'
        f'border-left:4px solid {color};border-radius:8px;'
        f'padding:10px 12px;margin:2px 0;">'
        f'<div style="font-weight:700;font-size:0.9rem;color:#1a1a30;">{data.get("name", "test")}</div>'
        f'<div style="color:{color};font-size:0.78rem;font-weight:600;">'
        f'{"✅ 正常" if status=="running" else "⚠️ 堆积" if status=="warning" else "🚨 超标"}'
        f'</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("吞吐(uph)", f"{data.get('throughput', 0):.0f}")
    c2.metric("DPPM", dppm_val)
    c3.metric("利用率", f"{data.get('utilization', 0)*100:.0f}%")

    bins = data.get("bin_distribution", {})
    if bins:
        st.caption(
            f"Bin分布: 良品{bins.get('bin1_good', 0)*100:.0f}% | "
            f"可修{bins.get('bin2_repairable', 0)*100:.0f}% | "
            f"报废{bins.get('bin3_scrap', 0)*100:.0f}%"
        )

    st.markdown("</div>", unsafe_allow_html=True)


def _render_adjustment_log():
    """渲染调整日志流"""
    st.markdown(
        '<div style="font-weight:700;font-size:0.85rem;color:#1a1a30;margin-bottom:6px;">'
        '📋 调整日志</div>',
        unsafe_allow_html=True,
    )

    sim = st.session_state.simulation_engine
    if sim and sim.adjustment_log:
        # 显示最近10条
        logs = sim.adjustment_log[-10:]
        logs.reverse()
        for entry in logs:
            tag = entry.get("type", "manual")
            tag_color = "#3d8af7" if tag == "manual" else "#00a878"
            st.markdown(
                f'<div style="font-size:0.72rem;padding:3px 0;border-bottom:1px solid #f0f0f0;">'
                f'<span style="color:{tag_color};font-weight:600;">[{tag}]</span> '
                f'{entry.get("time", "")} {entry.get("line", "")} '
                f'{entry.get("param", "")}: {entry.get("old_value", "?")} → {entry.get("new_value", "?")}<br/>'
                f'<span style="color:#667788;">{entry.get("reason", "")}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # 清空按钮
        if st.button("清空日志", key="clear_adj_log", use_container_width=True):
            sim.adjustment_log.clear()
            sim.auto_check_log.clear()
            st.rerun()
    else:
        st.caption("暂无调整记录")
```

- [ ] **Step 3: Add chart rendering functions**

```python
def _render_yield_chart():
    """渲染良率趋势折线图"""
    history = st.session_state.simulation_history
    if not history:
        st.caption("等待数据...")
        return

    chart_data = []
    for frame in history:
        ts = frame.get("timestamp", "")
        lines = frame.get("production_lines", {})
        for line_id in ["litho", "etch"]:
            data = lines.get(line_id, {})
            chart_data.append({
                "时间": ts,
                "产线": data.get("name", line_id),
                "良率": data.get("yield_rate", 0) * 100,
            })

    df = pd.DataFrame(chart_data)
    if df.empty:
        st.caption("等待数据...")
        return

    pivot = df.pivot(index="时间", columns="产线", values="良率")
    st.line_chart(pivot, height=250)


def _render_output_chart():
    """渲染产出台账柱状图"""
    history = st.session_state.simulation_history
    if not history:
        return

    # 取最近10帧做柱状图
    recent = history[-10:]
    chart_data = []
    for frame in recent:
        ts = frame.get("timestamp", "")
        lines = frame.get("production_lines", {})
        for line_id, data in lines.items():
            val = data.get("output", data.get("throughput", 0))
            chart_data.append({
                "时间": ts,
                "产线": data.get("name", line_id),
                "产出": val,
            })

    df = pd.DataFrame(chart_data)
    if df.empty:
        return

    pivot = df.pivot(index="时间", columns="产线", values="产出")
    st.bar_chart(pivot, height=200)


def _render_event_timeline():
    """渲染事件时间线"""
    sim = st.session_state.simulation_engine
    if not sim:
        return

    all_events = sim.event_log[-20:]
    all_events.reverse()

    if not all_events:
        st.caption("暂无事件记录")
        return

    for ev in all_events:
        ev_type = ev.get("type", "info")
        icon = {"alarm": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(ev_type, "📝")
        st.caption(f"{icon} {ev.get('time', '')} {ev.get('message', '')}")
```

- [ ] **Step 4: Add Tab2 content inside tab2 block**

After the `with tab1:` block, add:

```python
# ═══════════════════════════════════════════════════════════
# Tab 2: 产线监控
# ═══════════════════════════════════════════════════════════
with tab2:
    render_monitoring_dashboard()
```

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "feat: add Tab2 production line monitoring dashboard with charts and adjustment log"
```

---

### Task 10: 实现自动检测调整循环 + 联动推送

**Files:**
- Modify: `app.py` (add auto-check loop and linkage)

- [ ] **Step 1: Add auto-check function**

Add this function alongside the other simulation helpers:

```python
def run_auto_check():
    """执行一次自动检测调整循环（轻量级，不经过LangGraph）"""
    sim = st.session_state.simulation_engine
    if sim is None or not sim.is_running():
        return

    summary = sim.get_summary()
    alerts = []
    adjustments_made = []

    # 光刻线检测
    litho = summary.get("litho", {})
    if litho.get("yield_rate", 1) < 0.935:  # 基线96.5%，掉3%触发
        alerts.append("光刻线良率偏低")
        old_val = sim.litho.params.get("exposure_dose", 25.0)
        new_val = min(30.0, old_val + 1.5)
        sim.apply_adjustment("litho", "exposure_dose", new_val)
        adjustments_made.append({
            "time": time.strftime("%H:%M:%S"),
            "line": "litho",
            "param": "exposure_dose",
            "old_value": old_val,
            "new_value": new_val,
            "reason": "自动补偿：良率低于阈值，增加曝光剂量",
        })

    # 刻蚀线检测
    etch = summary.get("etch", {})
    if etch.get("yield_rate", 1) < 0.910:  # 基线94%，掉3%触发
        alerts.append("刻蚀线良率偏低")
        old_val = sim.etch.params.get("rf_power", 500.0)
        new_val = min(600.0, old_val + 30)
        sim.apply_adjustment("etch", "rf_power", new_val)
        adjustments_made.append({
            "time": time.strftime("%H:%M:%S"),
            "line": "etch",
            "param": "rf_power",
            "old_value": old_val,
            "new_value": new_val,
            "reason": "自动补偿：良率低于阈值，增加RF功率",
        })

    # 测试线检测
    test = summary.get("test", {})
    if test.get("dppm", 0) > 600:
        alerts.append(f"测试线DPPM超标({test['dppm']})")

    # OEE检测
    for line_id in ["litho", "etch"]:
        line_data = summary.get(line_id, {})
        if line_data.get("oee", 1) < 0.60:
            alerts.append(f"{'光刻' if line_id == 'litho' else '刻蚀'}线OEE告警")

    # 写入自动检测日志
    log_entry = {
        "time": time.strftime("%H:%M:%S"),
        "alerts": alerts,
        "adjustments": len(adjustments_made),
    }
    sim.auto_check_log.append(log_entry)

    # 写入调整日志
    for adj in adjustments_made:
        adj_with_type = dict(adj)
        adj_with_type["agent"] = "自动检测"
        adj_with_type["type"] = "auto"
        sim.adjustment_log.append(adj_with_type)

    # 联动：如果检测到异常，在聊天中推入系统消息
    if alerts or adjustments_made:
        msg_parts = [f"🤖 **[{log_entry['time']}] 自动检测结果**"]
        for a in alerts:
            msg_parts.append(f"⚠️ {a}")
        for adj in adjustments_made:
            msg_parts.append(
                f"🔧 已自动调整: {adj['line']}.{adj['param']} "
                f"({adj['old_value']:.1f} → {adj['new_value']:.1f}) — {adj['reason']}"
            )
        if not alerts:
            msg_parts.append("✅ 全部指标正常")

        st.session_state.messages.append({
            "role": "assistant",
            "content": "\n\n".join(msg_parts),
            "msg_type": "system_notification",
            "timestamp": time.strftime("%H:%M:%S"),
        })


def auto_check_loop():
    """自动检测循环（在后台线程中运行）"""
    while st.session_state.simulation_active:
        if st.session_state.auto_check_enabled:
            run_auto_check()
        # 等待指定的间隔
        interval = st.session_state.auto_check_interval
        for _ in range(interval):
            if not st.session_state.simulation_active:
                break
            time.sleep(1)
```

- [ ] **Step 2: Start auto-check thread in start_simulation**

In the `start_simulation()` function, after starting the simulation thread, add:

```python
    # 启动自动检测线程
    auto_thread = threading.Thread(target=auto_check_loop, daemon=True)
    auto_thread.start()
```

- [ ] **Step 3: Add system notification message rendering in chat**

In the chat message rendering loop (the `for msg in st.session_state.messages:` block), add handling for `msg_type == "system_notification"`:

After the `if msg_type == "workflow":` block, add:

```python
            elif msg_type == "system_notification":
                with st.chat_message("assistant", avatar="🤖"):
                    st.info(content)
```

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add auto-check loop and chat-monitoring linkage with system notifications"
```

---

### Task 11: 更新依赖文件

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Update `requirements.txt`**

Read the existing `requirements.txt` and ensure it has all dependencies. The current file has:

```
streamlit>=1.30.0
networkx>=3.0
matplotlib>=3.7.0
openai>=1.0.0
python-dotenv>=1.0.0
pandas>=2.0.0
langgraph>=0.2.0
langchain-openai>=0.1.0
duckduckgo-search>=6.0.0
python-docx>=1.0.0
openpyxl>=3.1.0
fpdf2>=2.7.0
requests>=2.31.0
pyyaml>=6.0
```

No new pip packages are strictly required (we use Streamlit native charts + pandas for data handling). Altair is optionally useful but not required for the MVP. The file can stay as-is unless we want to add altair for better chart control.

If adding altair for the adjustment marker lines feature:

```
altair>=5.0
```

- [ ] **Step 2: Install dependencies**

```bash
pip install -r requirements.txt
```

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: verify dependencies for production line monitoring system"
```

---

### Task 12: 端到端集成验证

- [ ] **Step 1: Start the app**

```bash
streamlit run app.py
```

- [ ] **Step 2: Verify basic functionality**

Checklist:
- [ ] Tab1 聊天界面正常显示，标题为"半导体产线智能监控与决策系统"
- [ ] 侧边栏示例按钮为产线场景（产线检测、自动调整、综合分析、故障诊断、生成报告）
- [ ] 点击"产线检测"按钮 → 触发工作流 → 聊天中出现诊断报告卡片
- [ ] Tab2 显示"产线仿真未启动"，点击"启动仿真"
- [ ] Tab2 三条产线指标卡片实时更新（光刻/刻蚀/测试）
- [ ] Tab2 良率趋势图、产出台账图正常渲染
- [ ] 等待仿真运行几分钟，事件时间线出现异常事件
- [ ] 自动检测调整触发，调整日志出现 `[auto]` 记录
- [ ] Tab1 聊天中出现系统推送消息（自动检测结果）
- [ ] Tab1 输入"调整光刻线曝光剂量+2" → 工作流执行 → Tab2调整日志出现 `[manual]` 记录
- [ ] 工作流完成后右侧面板出现报告下载按钮
- [ ] 下载的Word/Excel/PDF文件内容正确

- [ ] **Step 3: Fix any issues found**

```bash
git add -A
git commit -m "fix: end-to-end integration fixes for production line monitoring system"
```

---

**Plan complete.** Total: 12 tasks, estimated ~3-4 hours implementation time.
