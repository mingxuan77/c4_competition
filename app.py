"""半导体产线智能监控与决策系统 — Chat 主入口"""

import streamlit as st
import time
import threading
import pandas as pd

from simulation.semiconductor_sim import SemiconductorSimulator
from config import SIMULATION_CONFIG

st.set_page_config(
    page_title="半导体产线智能监控与决策系统",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── 自定义 CSS ─────────────────────────────────────────────
st.markdown("""
<style>
/* === 全局 === */
.stApp {
    background: #f2f4f7;
}

/* === 侧边栏 === */
[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e0e4ea;
}
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #4a4ae8;
    font-weight: 700;
}
[data-testid="stSidebar"] .stButton > button {
    background: #f5f6fa;
    color: #333350;
    border: 1px solid #d8dce6;
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.2s;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #eef0ff;
    border-color: #6c5ce7;
    color: #6c5ce7;
}

/* === 标题 === */
.main-header {
    background: linear-gradient(135deg, #5b4ae0 0%, #3d8af7 50%, #00a8a8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 1.9rem;
    font-weight: 800;
    margin: 0;
    letter-spacing: 0.5px;
}
.sub-header {
    color: #8899aa;
    font-size: 0.88rem;
    margin-top: -4px;
}

/* === 用户消息气泡 === */
.user-bubble {
    background: linear-gradient(135deg, #eef0ff 0%, #e4e8ff 100%);
    border: 1px solid #d0d4f0;
    border-radius: 14px 14px 4px 14px;
    padding: 12px 18px;
    margin: 6px 0;
    color: #1e1e38;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

/* === 助手消息气泡 === */
.assistant-bubble {
    background: #ffffff;
    border: 1px solid #e2e6ee;
    border-radius: 14px 14px 14px 4px;
    padding: 12px 18px;
    margin: 6px 0;
    color: #1a1a30;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

/* === 工作流结果卡片 === */
.workflow-card {
    background: #ffffff;
    border: 1px solid #d6e0e8;
    border-left: 4px solid #4a9cf7;
    border-radius: 10px;
    padding: 16px 20px;
    margin: 12px 0;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
.workflow-card h3 {
    color: #2a3a6e;
    margin-top: 0;
}
.workflow-card h4 {
    color: #4a5a8e;
}

/* === 按钮 === */
.stButton > button {
    font-weight: 600 !important;
    letter-spacing: 0.4px;
    transition: all 0.25s ease !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #5b4ae0, #3d8af7) !important;
    border: none !important;
    color: white !important;
    border-radius: 10px !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(90, 70, 220, 0.25) !important;
}

/* === 右侧面板 === */
.right-panel {
    background: #ffffff;
    border: 1px solid #e2e6ee;
    border-radius: 12px;
    padding: 16px;
    margin-top: 8px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.04);
}
.right-panel h3 {
    color: #2a2a4e;
    font-weight: 700;
    margin-top: 0;
}
.right-panel h4 {
    color: #3a3a5e;
}

/* === 滚动条 === */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #e8eaf0; }
::-webkit-scrollbar-thumb { background: #c0c5d0; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #a0a5b0; }

/* === 数据表格 === */
[data-testid="stDataFrame"] {
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #e0e4ea;
}

/* === Expander === */
[data-testid="stExpander"] {
    border: 1px solid #e2e6ee;
    border-radius: 10px;
    background: #fafbfc;
}

/* === 指标卡片 === */
[data-testid="stMetric"] {
    background: #fafbfc;
    border: 1px solid #e8ecf2;
    border-radius: 10px;
    padding: 10px !important;
}
[data-testid="stMetric"] label {
    color: #555577 !important;
}

/* === 聊天输入 === */
[data-testid="stChatInput"] textarea {
    border: 1px solid #d8dce6 !important;
    border-radius: 12px !important;
    color: #1a1a30 !important;
    background: #ffffff !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #6c5ce7 !important;
    box-shadow: 0 0 0 3px rgba(108,92,231,0.1) !important;
}

/* === 代码块 === */
.stCode {
    background: #f5f6fa !important;
    border: 1px solid #e2e6ee;
    border-radius: 8px;
}

/* === 标签 === */
.tag {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.76rem;
    font-weight: 600;
    margin-right: 4px;
}
.tag-success { background: #e0f5f0; color: #008866; }
.tag-running { background: #fff3e0; color: #cc7700; }
.tag-error { background: #ffe8e8; color: #cc3333; }
.tag-info { background: #e8eeff; color: #4455bb; }

/* === 分隔线 === */
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #d0d6e0, transparent);
    margin: 14px 0;
}

/* === 状态文字 === */
.stInfo, .stSuccess, .stWarning, .stError {
    color: #1a1a30 !important;
}
p, span, div, li, label, td, th {
    color: #1a1a30;
}
</style>
""", unsafe_allow_html=True)


# ─── Session State 初始化 ───────────────────────────────────
DEFAULTS = {
    "messages": [],           # [{role, content, msg_type, workflow_data, timestamp}]
    "workflow_logs": [],      # 最新一次工作流日志
    "workflow_results": {},   # 最新一次工作流结果
    "workflow_tasks": [],     # 最新一次工作流任务列表
    "workflow_intent": {},    # 最新一次意图解析结果
    "workflow_running": False,
    "executed_count": 0,
    # 产线仿真
    "simulation_engine": None,
    "simulation_active": False,
    "simulation_data": {},
    "simulation_history": [],
    "simulation_log": [],
    "auto_check_enabled": True,
    "auto_check_interval": SIMULATION_CONFIG["auto_check_default_interval"],
    "current_tab": "chat",
}
for key, default in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ─── 辅助函数 ───────────────────────────────────────────────

def build_workflow_response(user_input: str, intent_result: dict, tasks: list, results: dict) -> str:
    """将工作流执行结果组装成完整的自然语言报告。"""
    total = len(results)
    success = sum(1 for r in results.values() if r.get("status") == "success")
    failed = sum(1 for r in results.values() if r.get("status") == "failed")

    lines = [
        f'<div class="workflow-card">',
        f'<h3>📊 多Agent协同分析完成</h3>',
        f'<p>根据你的需求「<strong>{user_input[:60]}</strong>」，调度了 <strong>{total}</strong> 个专业子Agent协同完成分析，其中 {success} 个成功{f"、{failed} 个失败" if failed else ""}。</p>',
    ]

    # 提取策略报告
    strategy = None
    for r in results.values():
        if r.get("status") == "success":
            rd = r.get("result", {})
            if isinstance(rd, dict) and "strategy" in rd:
                strategy = rd["strategy"]
                break

    # 逐个任务结果
    sorted_ids = sorted(results.keys())
    for i, tid in enumerate(sorted_ids, 1):
        r = results[tid]
        if r.get("status") != "success":
            continue
        result_data = r.get("result", {})
        if not isinstance(result_data, dict):
            continue
        output = result_data.get("output", "")
        type_label = r.get("type_label", "")
        if output:
            lines.append(f"<p><strong>步骤{i} — {type_label}Agent：</strong><br/>{output}</p>")

    lines.append('</div>')

    # 策略报告详情
    if strategy:
        lines.append('<div class="workflow-card">')
        lines.append(f"<h3>🎯 综合分析结论</h3>")
        lines.append(f"<p>{strategy.get('executive_summary', '')}</p>")

        recs = strategy.get("recommendations", [])
        if recs:
            lines.append("<h4>📋 策略建议清单</h4>")
            for rec in recs:
                p = rec.get('priority', '')
                a = rec.get('action', '')
                r = rec.get('rationale', '')
                e = rec.get('estimated_impact', '')
                t = rec.get('timeline', '')
                lines.append(f"<p><strong>[{p}] {a}</strong><br/>")
                lines.append(f"依据: {r}<br/>预期效果: {e}<br/>时间线: {t}</p>")

        risk = strategy.get("risk_assessment", {})
        lines.append(f"<h4>⚡ 风险评估</h4>")
        lines.append(f"<p>整体风险等级: <strong>{risk.get('overall_risk_level', '-')}</strong></p>")
        for rk in risk.get("key_risks", []):
            lines.append(f"<p>- ⚠️ {rk}</p>")
        lines.append(f"<p>缓解措施: {risk.get('mitigation', '')}</p>")

        kpis = strategy.get("kpi_targets", {})
        if kpis:
            lines.append("<h4>📈 预期KPI指标</h4>")
            for k, v in kpis.items():
                lines.append(f"<p>- <strong>{k}</strong>: {v}</p>")

        lines.append(f"<h4>💡 总结</h4>")
        lines.append(f"<p>{strategy.get('conclusion', '')}</p>")
        lines.append('</div>')

    return "\n".join(lines)


def render_intent_visualization(intent_result: dict, tasks: list[dict] | None = None):
    """以任务流形式展示意图解析结果。"""
    import html

    tasks = tasks or []
    intent = html.escape(intent_result.get("intent", "已识别复合任务"))
    type_labels = {
        "retrieval": ("🔍", "数据检索"),
        "data_processing": ("🧹", "数据处理"),
        "ml_prediction": ("🤖", "机器学习"),
        "algorithm": ("⚙️", "算法优化"),
        "security": ("🛡️", "安全分析"),
        "code_execution": ("💻", "代码执行"),
        "network": ("🌐", "网络监控"),
        "database": ("🗄️", "数据库"),
        "strategy": ("📊", "策略输出"),
        "report_export": ("📄", "报告导出"),
    }

    nodes = []
    for index, task in enumerate(tasks):
        task_id = html.escape(str(task.get("task_id", "-")))
        task_type = task.get("task_type", task.get("type", "-"))
        icon, label = type_labels.get(task_type, ("🧩", str(task_type)))
        desc = html.escape(str(task.get("description", ""))[:52])
        deps = task.get("deps", [])
        dep_text = "无前置依赖" if not deps else "依赖 " + ", ".join(html.escape(str(dep)) for dep in deps)
        arrow = '<div class="intent-arrow">↓</div>' if index else ""
        nodes.append(
            arrow
            + f'<div class="intent-node">'
            + f'<div class="intent-node-head">'
            + f'<span class="intent-node-id">{task_id}</span>'
            + f'<span>{icon} {html.escape(label)}</span>'
            + f'</div>'
            + f'<div class="intent-node-desc">{desc}</div>'
            + f'<div class="intent-node-deps">{dep_text}</div>'
            + f'</div>'
        )

    node_html = "\n".join(nodes) if nodes else '<div class="intent-node-deps">正在生成任务节点...</div>'
    visual_html = (
        "<style>"
        ".intent-visual{border:1px solid #dbe4ee;border-radius:10px;background:#fbfcff;padding:12px;margin:8px 0 12px;}"
        ".intent-core{border-left:4px solid #5b4ae0;background:#ffffff;padding:10px 12px;border-radius:8px;font-weight:700;color:#202040;margin-bottom:10px;}"
        ".intent-node{border:1px solid #d7deea;background:#ffffff;border-radius:8px;padding:9px 10px;box-shadow:0 1px 4px rgba(20,30,60,0.05);}"
        ".intent-node-head{display:flex;align-items:center;gap:8px;font-size:0.86rem;font-weight:700;color:#26264a;}"
        ".intent-node-id{display:inline-flex;align-items:center;justify-content:center;min-width:24px;height:24px;border-radius:50%;background:#e9ecff;color:#4b45c8;font-weight:800;}"
        ".intent-node-desc{margin-top:6px;font-size:0.78rem;line-height:1.35;color:#384058;}"
        ".intent-node-deps{margin-top:5px;font-size:0.72rem;color:#758095;}"
        ".intent-arrow{text-align:center;color:#8490aa;line-height:1.3;font-weight:800;}"
        "</style>"
        f'<div class="intent-visual"><div class="intent-core">🧠 {intent}</div>{node_html}</div>'
    )
    st.markdown(visual_html, unsafe_allow_html=True)


def render_workflow_stage(
    stage: str,
    progress: int,
    logs: list[dict] | None = None,
    intent_result: dict | None = None,
    tasks: list[dict] | None = None,
):
    """渲染工作流执行中的阶段状态。"""
    logs = logs or []
    tasks = tasks or []

    st.info("⚡ **多Agent协同工作中...**")
    st.progress(progress, text=stage)

    st.markdown("#### 🧭 阶段进度")
    stage_rows = [
        ("意图解析", 25),
        ("任务拆解", 45),
        ("Agent调度", 70),
        ("结果汇总", 95),
    ]
    for name, threshold in stage_rows:
        marker = "✅" if progress >= threshold else "🔄" if name in stage else "⏳"
        st.caption(f"{marker} {name}")

    if intent_result:
        st.markdown("#### 🧠 意图解析")
        render_intent_visualization(intent_result, tasks)

    if tasks:
        st.markdown("#### 🧩 任务拆解")
        import pandas as pd
        rows = []
        for task in tasks:
            rows.append({
                "ID": task.get("task_id", "-"),
                "类型": task.get("task_type", task.get("type", "-")),
                "依赖": ", ".join(task.get("deps", [])) or "无",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=min(len(rows) * 38 + 38, 260))

    if logs:
        st.markdown("#### 📜 实时日志")
        log_text = ""
        for entry in logs[-10:]:
            level_icon = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}.get(entry["level"], "📝")
            tid_str = f" [{entry['task_id']}]" if entry.get("task_id") else ""
            ts = entry.get("timestamp", "")
            log_text += f"{ts} {level_icon}{tid_str} {entry['message']}\n"
        st.code(log_text, language=None)


def execute_workflow(user_input: str, status_callback=None) -> tuple[str, dict, list, list, dict]:
    """使用 LangChain + LangGraph 执行 Meta-Agent → Worker 调度流程。"""
    from config import LLM_CONFIG

    logs = []
    logs.append({"timestamp": time.strftime("%H:%M:%S"), "level": "INFO",
                 "message": f"🚀 [LangGraph] 启动工作流: {user_input[:50]}...", "task_id": None})
    if status_callback:
        status_callback("🔍 意图解析中...", 10, logs, None, [])

    # 步骤1: 意图解析（优先使用 LangChain structured output）
    from meta_agent.langgraph_engine import parse_intent_with_langchain

    langchain_result = parse_intent_with_langchain(user_input)
    if langchain_result:
        intent_result = langchain_result
        logs.append({"timestamp": time.strftime("%H:%M:%S"), "level": "SUCCESS",
                     "message": f"[LangChain] 意图识别: {intent_result['intent']}", "task_id": None})
        # 任务已由 LangChain 标准化，跳过 TaskPlanner
        tasks = intent_result["tasks"]
    else:
        # 回退到规则匹配
        from meta_agent.intent_parser import IntentParser
        parser = IntentParser()
        intent_result = parser.parse(user_input)
        logs.append({"timestamp": time.strftime("%H:%M:%S"), "level": "SUCCESS",
                     "message": f"[规则匹配] 意图识别: {intent_result.get('intent', '')}", "task_id": None})
        from meta_agent.task_planner import TaskPlanner
        tasks = TaskPlanner().plan(intent_result)

    if status_callback:
        status_callback("✅ 意图解析完成", 35, logs, intent_result, tasks)

    logs.append({"timestamp": time.strftime("%H:%M:%S"), "level": "INFO",
                 "message": f"任务拆解: {len(tasks)} 个子任务", "task_id": None})
    if status_callback:
        status_callback("🧩 任务拆解完成", 50, logs, intent_result, tasks)

    # 步骤2: 注入仿真数据到产线相关任务
    for task in tasks:
        if task.get("task_type") in ("production_monitor", "production_adjuster"):
            task.setdefault("params", {})
            task["params"]["simulation_snapshot"] = st.session_state.get("simulation_data", {})
            task["params"]["simulation_history"] = st.session_state.get("simulation_history", [])

    # 步骤3: LangGraph 并行调度执行（替代旧的 DAGBuilder + Scheduler + threading）
    from meta_agent.langgraph_engine import run_with_langgraph
    if status_callback:
        status_callback("🚀 Agent调度执行中...", 70, logs, intent_result, tasks)
    engine_result = run_with_langgraph(tasks, user_input)
    results = engine_result["results"]
    logs.extend(engine_result["logs"])
    if status_callback:
        status_callback("📦 结果汇总中...", 95, logs, intent_result, tasks)

    response = build_workflow_response(user_input, intent_result, tasks, results)
    if status_callback:
        status_callback("✅ 工作流执行完成", 100, logs, intent_result, tasks)
    return response, results, tasks, logs, intent_result


# ─── Tab2 监控仪表盘渲染函数 ─────────────────────────────

def _render_monitoring_dashboard():
    """渲染 Tab2: 产线监控仪表盘"""

    # === 控制栏 ===
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([0.3, 0.25, 0.45])
    with ctrl_col1:
        sim_active = st.session_state.simulation_active
        btn_label = "⏸️ 停止仿真" if sim_active else "▶️ 启动仿真"
        if st.button(btn_label, use_container_width=True,
                     type="primary" if not sim_active else "secondary"):
            toggle_simulation()
    with ctrl_col2:
        auto_enabled = st.toggle(
            "🔁 自动检测调整",
            value=st.session_state.auto_check_enabled,
            help="开启后每N分钟自动检测产线异常并执行轻量级调整"
        )
        st.session_state.auto_check_enabled = auto_enabled
        interval_min = st.selectbox(
            "间隔(分钟)", [3, 5, 10], index=1,
            key="auto_interval_selector", label_visibility="collapsed"
        )
        st.session_state.auto_check_interval = interval_min * 60
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
            <p style="font-size:0.85rem;">点击上方「启动仿真」按钮开始监控三条产线的实时数据</p>
        </div>
        """, unsafe_allow_html=True)

    # 仿真运行时自动刷新Tab2（每秒更新一次图表）
    if st.session_state.simulation_active:
        time.sleep(1)
        st.rerun()


def _render_line_card(line_id: str, data: dict):
    """渲染光刻/刻蚀产线指标卡片"""
    if not data:
        st.caption("无数据")
        return

    status = data.get("status", "running")
    color = {
        "running": "#00a878", "warning": "#e8a020",
        "alarm": "#e04040", "idle": "#8899aa",
    }.get(status, "#8899aa")

    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #e0e4ea;'
        f'border-left:4px solid {color};border-radius:8px;'
        f'padding:10px 12px;margin:2px 0;">'
        f'<div style="font-weight:700;font-size:0.9rem;color:#1a1a30;">'
        f'{data.get("name", line_id)}</div>'
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
    color = {"running": "#00a878", "warning": "#e8a020", "alarm": "#e04040"}.get(status)

    st.markdown(
        f'<div style="background:#ffffff;border:1px solid #e0e4ea;'
        f'border-left:4px solid {color};border-radius:8px;'
        f'padding:10px 12px;margin:2px 0;">'
        f'<div style="font-weight:700;font-size:0.9rem;color:#1a1a30;">'
        f'{data.get("name", "test")}</div>'
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
        logs = sim.adjustment_log[-10:]
        logs.reverse()
        for entry in logs:
            tag = entry.get("type", "manual")
            tag_color = "#3d8af7" if tag == "manual" else "#00a878"
            st.markdown(
                f'<div style="font-size:0.72rem;padding:3px 0;border-bottom:1px solid #f0f0f0;">'
                f'<span style="color:{tag_color};font-weight:600;">[{tag}]</span> '
                f'{entry.get("time", "")} {entry.get("line", "")} '
                f'{entry.get("param", "")}: {entry.get("old_value", "?")} → '
                f'{entry.get("new_value", "?")}<br/>'
                f'<span style="color:#667788;">{entry.get("reason", "")}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        if st.button("清空日志", key="clear_adj_log", use_container_width=True):
            sim.adjustment_log.clear()
            sim.auto_check_log.clear()
            st.rerun()
    else:
        st.caption("暂无调整记录")


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
        return
    pivot = df.pivot(index="时间", columns="产线", values="良率")
    st.line_chart(pivot, height=250)


def _render_output_chart():
    """渲染产出台账柱状图"""
    history = st.session_state.simulation_history
    if not history:
        return

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


# ─── 仿真生命周期管理 ───────────────────────────────────────

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
        while st.session_state.simulation_active and sim.is_running():
            frame = sim.tick()
            st.session_state.simulation_data = frame
            st.session_state.simulation_history.append(frame)
            max_frames = SIMULATION_CONFIG["history_max_frames"]
            if len(st.session_state.simulation_history) > max_frames:
                st.session_state.simulation_history = (
                    st.session_state.simulation_history[-max_frames:]
                )
            time.sleep(SIMULATION_CONFIG["tick_interval_seconds"])

    sim_thread = threading.Thread(target=_sim_loop, daemon=True)
    sim_thread.start()

    # 启动自动检测线程
    auto_thread = threading.Thread(target=auto_check_loop, daemon=True)
    auto_thread.start()


def stop_simulation():
    """停止产线仿真引擎"""
    if st.session_state.simulation_engine:
        st.session_state.simulation_engine.stop()
    st.session_state.simulation_active = False


def toggle_simulation():
    """切换仿真启停状态"""
    if st.session_state.simulation_active:
        stop_simulation()
        st.rerun()
    else:
        start_simulation()
        # 等待后台线程产出第一帧数据
        waited = 0
        while waited < 3:
            time.sleep(0.5)
            waited += 0.5
            if st.session_state.simulation_data.get("production_lines"):
                break
        st.rerun()


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
    if litho.get("yield_rate", 1) < 0.935:
        alerts.append("光刻线良率偏低")
        old_val = sim.litho.params.get("exposure_dose", 25.0)
        new_val = min(30.0, old_val + 1.5)
        sim.apply_adjustment("litho", "exposure_dose", new_val)
        adjustments_made.append({
            "time": time.strftime("%H:%M:%S"),
            "line": "litho", "param": "exposure_dose",
            "old_value": old_val, "new_value": new_val,
            "reason": "自动补偿：良率低于阈值，增加曝光剂量",
        })

    # 刻蚀线检测
    etch = summary.get("etch", {})
    if etch.get("yield_rate", 1) < 0.910:
        alerts.append("刻蚀线良率偏低")
        old_val = sim.etch.params.get("rf_power", 500.0)
        new_val = min(600.0, old_val + 30)
        sim.apply_adjustment("etch", "rf_power", new_val)
        adjustments_made.append({
            "time": time.strftime("%H:%M:%S"),
            "line": "etch", "param": "rf_power",
            "old_value": old_val, "new_value": new_val,
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
            name = "光刻" if line_id == "litho" else "刻蚀"
            alerts.append(f"{name}线OEE告警({line_data['oee']*100:.0f}%)")

    # 写入日志
    log_entry = {
        "time": time.strftime("%H:%M:%S"),
        "alerts": alerts,
        "adjustments": len(adjustments_made),
    }
    sim.auto_check_log.append(log_entry)

    for adj in adjustments_made:
        adj_with_type = dict(adj)
        adj_with_type["agent"] = "自动检测"
        adj_with_type["type"] = "auto"
        sim.adjustment_log.append(adj_with_type)

    # 推送系统消息到聊天
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
    """自动检测循环（后台线程）"""
    while st.session_state.simulation_active:
        if st.session_state.auto_check_enabled:
            run_auto_check()
        interval = st.session_state.auto_check_interval
        for _ in range(interval):
            if not st.session_state.simulation_active:
                break
            time.sleep(1)


# ─── 侧边栏 ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 系统配置")

    from config import LLM_CONFIG

    with st.expander("🔑 LLM 设置", expanded=False):
        use_llm = st.checkbox(
            "启用 LLM 模式",
            value=LLM_CONFIG["enabled"],
            help="关闭则使用内置规则匹配与模拟数据",
        )
        model = st.text_input("模型", value=LLM_CONFIG["model"])

        if use_llm:
            api_key = st.text_input(
                "DeepSeek API Key",
                value=LLM_CONFIG["api_key"],
                type="password",
            )
            base_url = st.text_input("API Base URL", value=LLM_CONFIG["base_url"])
        else:
            api_key = ""
            base_url = ""

        # 实时更新 LLM 配置
        LLM_CONFIG["enabled"] = use_llm
        if api_key:
            LLM_CONFIG["api_key"] = api_key
        if base_url:
            LLM_CONFIG["base_url"] = base_url
        LLM_CONFIG["model"] = model

    st.markdown("---")
    st.markdown("### 💡 示例任务")
    examples = [
        ("🔍 产线检测", "全面检测三条产线的运行状态，分析良率和产能异常"),
        ("🔧 自动调整", "光刻线良率持续下降，分析原因并自动调整工艺参数"),
        ("📊 综合分析", "对刻蚀线和测试线进行联合分析，找出良率瓶颈"),
        ("⚡ 故障诊断", "设备OEE突然下降，排查是待料问题还是设备故障"),
        ("📝 生成报告", "生成本周产线运行综合报告，包含趋势和建议"),
    ]
    for label, ex in examples:
        if st.button(label, key=f"ex_{label}", use_container_width=True):
            st.session_state.pending_input = ex
            st.rerun()

    st.markdown("---")
    if st.button("🗑️ 清空对话", use_container_width=True):
        st.session_state.messages = []
        st.session_state.workflow_results = {}
        st.session_state.workflow_logs = []
        st.session_state.workflow_tasks = []
        st.session_state.workflow_intent = {}
        st.session_state.workflow_running = False
        st.rerun()

    st.caption(f"已对话 {len(st.session_state.messages)} 轮 | 执行 {st.session_state.executed_count} 次工作流")


# ─── Tab 切换 ─────────────────────────────────────────────
tab1, tab2 = st.tabs(["💬 智能对话", "📊 产线监控"])

# ═══════════════════════════════════════════════════════════
# Tab 1: 智能对话
# ═══════════════════════════════════════════════════════════
with tab1:
    col_main, col_right = st.columns([2.2, 1], gap="medium")

with col_main:
    # 标题
    st.markdown('<p class="main-header">🏭 半导体产线智能监控与决策系统</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Internet of Agents — Production Line Monitoring & Decision Platform</p>', unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # 聊天历史
    chat_area = st.container()
    with chat_area:
        if not st.session_state.messages:
            st.markdown("""
            <div style="text-align:center; padding:40px 20px; color:#667788;">
                <p style="font-size:3rem; margin-bottom:10px;">🏭</p>
                <p style="font-size:1.2rem; font-weight:600; color:#4a4ae8;">半导体产线智能监控与决策系统</p>
                <p style="font-size:0.9rem;">基于多Agent协同的产线状态检测 · 异常诊断 · 工艺调整 · 决策报告</p>
                <p style="font-size:0.8rem; color:#8899aa;">支持：光刻线 · 刻蚀线 · 测试线 | 实时监控 + 智能分析 + 自动调整</p>
            </div>
            """, unsafe_allow_html=True)

        for msg in st.session_state.messages:
            role = msg["role"]
            msg_type = msg.get("msg_type", "chat")
            content = msg["content"]

            if msg_type == "workflow":
                # 工作流结果用自定义卡片展示
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(content, unsafe_allow_html=True)
                    if msg.get("workflow_results"):
                        with st.expander("📋 查看执行详情与各Agent输出", expanded=False):
                            results = msg["workflow_results"]
                            tasks = msg.get("workflow_tasks", [])

                            # 摘要指标
                            total = len(results)
                            success = sum(1 for r in results.values() if r.get("status") == "success")
                            c1, c2, c3 = st.columns(3)
                            c1.metric("总任务", total)
                            c2.metric("成功", success)
                            c3.metric("失败", total - success)

                            # 任务分配表
                            import pandas as pd
                            rows = []
                            for tid in sorted(results.keys()):
                                r = results[tid]
                                desc = ""
                                for t in tasks:
                                    if t.get("task_id") == tid:
                                        desc = t.get("description", "")
                                        break
                                rows.append({
                                    "任务": tid,
                                    "Agent": r.get("worker_name", "-"),
                                    "类型": r.get("type_label", "-"),
                                    "状态": "✅" if r.get("status") == "success" else "❌",
                                    "工作内容": desc[:40] + ("..." if len(desc) > 40 else ""),
                                })
                            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                            # 各Agent详细输出
                            for tid in sorted(results.keys()):
                                r = results[tid]
                                if r.get("status") != "success":
                                    continue
                                result_data = r.get("result", {})
                                if not isinstance(result_data, dict):
                                    continue
                                if "strategy" in result_data:
                                    continue

                                type_label = r.get("type_label", "")
                                output = result_data.get("output", "")
                                st.markdown(f"**✅ {tid} — {type_label}**（{r.get('worker_name', '')}）")
                                if output:
                                    st.info(output)
                                st.markdown("---")
            elif msg_type == "system_notification":
                # 系统自动推送消息（自动检测结果等）
                with st.chat_message("assistant", avatar="🤖"):
                    st.info(content)
            else:
                # 普通聊天消息
                avatar = "🧑" if role == "user" else "🤖"
                with st.chat_message(role, avatar=avatar):
                    st.markdown(content)

    # 输入区域
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # 处理预设输入
    if "pending_input" in st.session_state and st.session_state.pending_input:
        prompt = st.session_state.pending_input
        st.session_state.pending_input = None
    else:
        prompt = st.chat_input("输入你的任务或问题...", key="main_chat_input")

    if prompt:
        prompt = prompt.strip()
        # 添加用户消息
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "msg_type": "chat",
            "timestamp": time.strftime("%H:%M:%S"),
        })

        # 判断是工作流请求还是普通对话
        from meta_agent.chat_llm import is_workflow_request, ChatLLM

        if is_workflow_request(prompt):
            # 执行工作流
            st.session_state.workflow_running = True
            st.rerun()
        else:
            # 普通对话
            chat_llm = ChatLLM()
            with st.spinner("思考中..."):
                reply = chat_llm.chat(prompt, st.session_state.messages[:-1])
            st.session_state.messages.append({
                "role": "assistant",
                "content": reply,
                "msg_type": "chat",
                "timestamp": time.strftime("%H:%M:%S"),
            })
            st.rerun()

# ─── 右侧面板 ───────────────────────────────────────────────
with col_right:
    st.markdown("### 📡 工作流执行状态")

    # 如果在执行中（由 st.rerun 触发后的执行）
    if st.session_state.workflow_running:
        # 获取触发工作流的最后一条用户消息
        last_user_msg = ""
        for msg in reversed(st.session_state.messages):
            if msg["role"] == "user":
                last_user_msg = msg["content"]
                break

        if last_user_msg:
            progress_placeholder = st.empty()

            def update_workflow_stage(stage, progress, logs=None, intent_result=None, tasks=None):
                with progress_placeholder.container():
                    render_workflow_stage(stage, progress, logs, intent_result, tasks)

            response_html, results, tasks, logs, intent_result = execute_workflow(
                last_user_msg,
                status_callback=update_workflow_stage,
            )

            progress_placeholder.empty()
            st.success(f"✅ 执行完成！共 {len(results)} 个子任务")

            # 存储结果
            st.session_state.workflow_results = results
            st.session_state.workflow_logs = logs
            st.session_state.workflow_tasks = tasks
            st.session_state.workflow_intent = intent_result
            st.session_state.workflow_running = False
            st.session_state.executed_count += 1

            # 添加工作流结果到聊天
            st.session_state.messages.append({
                "role": "assistant",
                "content": response_html,
                "msg_type": "workflow",
                "workflow_results": results,
                "workflow_tasks": tasks,
                "timestamp": time.strftime("%H:%M:%S"),
            })
            st.rerun()

    # 显示最新工作流状态
    if st.session_state.workflow_results:
        results = st.session_state.workflow_results
        total = len(results)
        success_count = sum(1 for r in results.values() if r.get("status") == "success")
        failed_count = sum(1 for r in results.values() if r.get("status") == "failed")

        st.markdown('<div class="right-panel">', unsafe_allow_html=True)
        st.markdown("#### 📊 任务执行摘要")
        c1, c2, c3 = st.columns(3)
        c1.metric("总计", total)
        c2.metric("成功", success_count)
        c3.metric("失败", failed_count, delta_color="inverse")

        intent_result = st.session_state.workflow_intent
        if intent_result:
            st.markdown("#### 🧠 意图解析")
            render_intent_visualization(intent_result, st.session_state.workflow_tasks)

        tasks = st.session_state.workflow_tasks
        if tasks:
            st.markdown("#### 🧩 任务拆解")
            import pandas as pd
            task_rows = []
            for task in tasks:
                task_rows.append({
                    "ID": task.get("task_id", "-"),
                    "类型": task.get("task_type", task.get("type", "-")),
                    "依赖": ", ".join(task.get("deps", [])) or "无",
                })
            st.dataframe(pd.DataFrame(task_rows), use_container_width=True, hide_index=True, height=min(len(task_rows) * 38 + 38, 260))

        # 任务状态表
        import pandas as pd
        rows = []
        for tid in sorted(results.keys()):
            r = results[tid]
            status_icon = "✅" if r.get("status") == "success" else "❌" if r.get("status") == "failed" else "⏭️"
            rows.append({
                "ID": tid,
                "": status_icon,
                "Agent": r.get("type_label", "-"),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=min(len(rows) * 38 + 38, 300))

        # 日志流
        logs = st.session_state.workflow_logs
        if logs:
            st.markdown("#### 📜 执行日志")
            log_text = ""
            for entry in logs[-25:]:
                level_icon = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}.get(entry["level"], "📝")
                tid_str = f" [{entry['task_id']}]" if entry.get("task_id") else ""
                ts = entry.get("timestamp", "")
                log_text += f"{ts} {level_icon}{tid_str} {entry['message']}\n"
            st.code(log_text, language=None)

        # ── 文件下载区域 ──
        all_files = []
        for tid in sorted(results.keys()):
            r = results[tid]
            if r.get("status") != "success":
                continue
            result_data = r.get("result", {})
            if not isinstance(result_data, dict):
                continue
            files = result_data.get("generated_files", [])
            if files:
                all_files.extend(files)

        if all_files:
            st.markdown("#### 📥 下载报告文件")
            import base64
            import zipfile
            import io

            for fpath in all_files:
                fname = fpath.replace("\\", "/").split("/")[-1]
                try:
                    with open(fpath, "rb") as f:
                        fdata = f.read()
                    fsize_kb = round(len(fdata) / 1024, 1)
                    ext = fname.rsplit(".", 1)[-1] if "." in fname else ""
                    icon = {"docx": "📄", "xlsx": "📊", "pdf": "📕"}.get(ext, "📎")
                    col1, col2, col3 = st.columns([0.4, 0.3, 0.3])
                    col1.caption(f"{icon} {fname}")
                    col2.caption(f"{fsize_kb} KB")
                    col3.download_button(
                        label="下载",
                        data=fdata,
                        file_name=fname,
                        mime={
                            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "pdf": "application/pdf",
                        }.get(ext, "application/octet-stream"),
                        key=f"dl_{fname}",
                        use_container_width=True,
                    )
                except Exception:
                    st.caption(f"⚠️ 无法读取: {fname}")

            # 打包下载
            if len(all_files) > 1:
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for fpath in all_files:
                        fname = fpath.replace("\\", "/").split("/")[-1]
                        try:
                            with open(fpath, "rb") as f:
                                zf.writestr(fname, f.read())
                        except Exception:
                            pass
                st.download_button(
                    label="📦 打包下载全部文件 (ZIP)",
                    data=zip_buf.getvalue(),
                    file_name="analysis_report_pack.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="right-panel">', unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align:center; padding:30px 10px; color:#8899aa;">
            <p style="font-size:2rem;">📡</p>
            <p style="font-size:0.9rem;">暂无执行中的工作流</p>
            <p style="font-size:0.8rem;">在左侧输入一个分析任务<br/>系统将自动调度多Agent协同工作</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # 系统能力展示
        st.markdown("---")
        st.markdown("#### 🧩 可用Agent")
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
        for icon, name, desc in agents:
            st.caption(f"{icon} **{name}** — {desc}")


# ═══════════════════════════════════════════════════════════
# Tab 2: 产线监控仪表盘
# ═══════════════════════════════════════════════════════════
with tab2:
    _render_monitoring_dashboard()
