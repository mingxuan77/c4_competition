"""任务输入面板 - 用户输入与系统配置"""

import streamlit as st
from config import LLM_CONFIG


def render_input_panel() -> tuple[str, dict]:
    """渲染输入面板，返回 (用户输入, 配置选项)。"""

    # 初始化 session_state
    if "text_input_value" not in st.session_state:
        st.session_state.text_input_value = ""

    st.markdown("## 任务输入")

    with st.expander("⚙️  系统配置", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            use_llm = st.checkbox(
                "启用 LLM 意图解析",
                value=LLM_CONFIG["enabled"],
                help="关闭则使用内置规则匹配（mock模式）",
            )
        with col2:
            model = st.text_input("模型", value=LLM_CONFIG["model"])

        if use_llm:
            col3, col4 = st.columns(2)
            with col3:
                api_key = st.text_input(
                    "DeepSeek API Key",
                    value=LLM_CONFIG["api_key"],
                    type="password",
                )
            with col4:
                base_url = st.text_input(
                    "API Base URL",
                    value=LLM_CONFIG["base_url"],
                    help="DeepSeek 兼容 OpenAI 接口格式",
                )
        else:
            api_key = ""
            base_url = ""

    # 预设示例
    st.markdown("### 输入任务描述")
    examples = [
        "分析上海未来五年房价趋势并生成投资规划",
        "优化数据中心网络路由策略",
        "对用户行为数据进行清洗和建模分析",
    ]
    cols = st.columns(len(examples))
    for i, (col, ex) in enumerate(zip(cols, examples)):
        if col.button(f"示例{i+1}", key=f"ex_{i}", use_container_width=True):
            st.session_state.text_input_value = ex

    user_input = st.text_area(
        "用自然语言描述你的任务需求：",
        key="text_input_value",
        height=120,
        placeholder="例如：分析上海未来五年房价趋势并生成投资规划...",
    )

    config = {
        "use_llm": use_llm,
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
    }

    return user_input.strip(), config
