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
                    f"- Bin分布: "
                    f"良品{data.get('bin_distribution',{}).get('bin1_good',0)*100:.1f}%"
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
            user_prompt += "\n\n## 异常告警\n" + "\n".join(
                f"- ⚠️ {a}" for a in alerts
            )

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
                    alerts.append(f"测试线 DPPM 超标 ({dppm})，阈值600")
                if data.get("utilization", 0) > 0.95:
                    alerts.append(
                        f"测试线利用率过高 "
                        f"({data['utilization']*100:.1f}%)，存在堆积风险"
                    )
            else:
                y = data.get("yield_rate", 1)
                if y < 0.90:
                    alerts.append(
                        f"{data.get('name', line_id)} 良率严重偏低 "
                        f"({y*100:.1f}%)"
                    )
                elif y < 0.94:
                    alerts.append(
                        f"{data.get('name', line_id)} 良率偏低 "
                        f"({y*100:.1f}%)"
                    )
                oee = data.get("oee", 1)
                if oee < 0.60:
                    alerts.append(
                        f"{data.get('name', line_id)} OEE告警 "
                        f"({oee*100:.1f}%)"
                    )
        return alerts

    def _analyze_trends(self, history: list[dict]) -> str:
        """分析最近N帧数据的趋势"""
        if not history:
            return ""

        parts = []
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
                name = (
                    first.get("production_lines", {})
                    .get(line_id, {})
                    .get("name", line_id)
                )
                parts.append(
                    f"- {name}: 良率{direction} {abs(delta):.2f}个百分点"
                )

        return "\n".join(parts) if parts else "趋势正常，无明显异常变化"
