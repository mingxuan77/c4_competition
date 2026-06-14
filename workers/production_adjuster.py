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
            f"## 异常告警\n"
            + "\n".join(f"- {a}" for a in alerts)
            + "\n"
            f"## 上游诊断\n"
            + "\n".join(upstream_outputs[:3])
            + "\n\n请给出具体的工艺参数调整方案。"
        )

        llm_result = self._call_llm(
            system_prompt=(
                "你是半导体工艺工程师。根据产线异常数据，给出具体可量化的"
                "工艺参数调整方案。\n\n"
                "可调参数范围：\n"
                "- 光刻线(litho): exposure_dose (20-30 mJ/cm²), "
                "focus_offset (0-50 nm)\n"
                "- 刻蚀线(etch): rf_power (400-600 W), "
                "chamber_pressure (20-50 mTorr)\n"
                "- 测试线(test): sampling_rate (50-100 %)\n\n"
                "规则：\n"
                "1. 良率偏低 → 优先调整曝光剂量(光刻)或RF功率(刻蚀)\n"
                "2. 每次调整幅度不宜过大（曝光剂量±2以内, RF功率±50以内）\n"
                "3. 同时调整最多2个参数\n"
                "4. 每个调整给出理由\n\n"
                "输出严格JSON格式（不要markdown标记）：\n"
                '{"adjustments": [{"line": "litho", "param": "exposure_dose", '
                '"old_value": 25.0, "new_value": 26.5, '
                '"reason": "补偿光刻胶老化"}], '
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
                f"- {a['line']}.{a['param']}: "
                f"{a['old_value']} → {a['new_value']} ({a['reason']})"
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
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        try:
            return json.loads(text)
        except json.JSONDecodeError:
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
