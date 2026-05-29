"""跨域分布式多智能体协同调度系统 — Chat 主入口"""

import streamlit as st
import time

st.set_page_config(
    page_title="多智能体协同调度系统",
    page_icon="🤖",
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

    # 步骤2: LangGraph 并行调度执行（替代旧的 DAGBuilder + Scheduler + threading）
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
        ("🏠 房产投资", "分析上海未来五年房价趋势并生成投资规划"),
        ("🌐 网络优化", "优化数据中心网络路由策略，分析瓶颈与安全问题"),
        ("📊 数据分析", "对用户行为数据进行清洗和建模分析"),
        ("🛡️ 安全审计", "对信息系统进行安全漏洞扫描与合规审计"),
        ("🗄️ 数据库迁移", "分析数据库架构并进行迁移优化"),
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


# ─── 主布局 ─────────────────────────────────────────────────
col_main, col_right = st.columns([2.2, 1], gap="medium")

with col_main:
    # 标题
    st.markdown('<p class="main-header">🤖 跨域分布式多智能体协同调度系统</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Internet of Agents — Meta-Agent Orchestration Platform</p>', unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # 聊天历史
    chat_area = st.container()
    with chat_area:
        if not st.session_state.messages:
            st.markdown("""
            <div style="text-align:center; padding:40px 20px; color:#667788;">
                <p style="font-size:3rem; margin-bottom:10px;">🤖</p>
                <p style="font-size:1.2rem; font-weight:600; color:#4a4ae8;">欢迎使用多智能体协同调度系统</p>
                <p style="font-size:0.9rem;">输入你的任务需求，系统将自动调度多个专业Agent协同完成分析</p>
                <p style="font-size:0.8rem; color:#8899aa;">支持：数据分析 · 安全评估 · 网络优化 · 投资规划 · 数据库迁移 · 更多...</p>
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
            ("🔍", "数据检索", "多源数据搜索获取"),
            ("🧹", "数据处理", "清洗/ETL/特征工程"),
            ("🤖", "机器学习", "预测/分类/回归"),
            ("⚙️", "算法优化", "路径/组合/调度"),
            ("🛡️", "安全分析", "漏洞扫描/风险评估"),
            ("🌐", "网络监控", "拓扑/流量/异常"),
            ("🗄️", "数据库", "查询优化/迁移"),
            ("💻", "代码执行", "沙箱安全执行"),
            ("📊", "策略输出", "综合报告/建议"),
        ]
        for icon, name, desc in agents:
            st.caption(f"{icon} **{name}** — {desc}")
