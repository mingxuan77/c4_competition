"""状态面板 - 展示执行日志和进度"""

import streamlit as st
import pandas as pd


def render_status_panel(logs: list[dict], results: dict[str, dict] | None = None):
    st.markdown("## 📡 实时状态")

    # 任务执行进度
    if results:
        rows = []
        for tid, r in results.items():
            rows.append({
                "任务ID": tid,
                "状态": "✅ 成功" if r.get("status") == "success"
                       else "❌ 失败" if r.get("status") == "failed"
                       else r.get("status", "-"),
                "子Agent": r.get("worker_name", "-"),
                "类型": r.get("type_label", "-"),
            })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # 日志流
    st.markdown("### 📜 执行日志")
    if logs:
        log_container = st.container(height=320)
        with log_container:
            for entry in logs[-40:]:
                level_icon = {
                    "INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️",
                }.get(entry["level"], "📝")
                tid_str = f" `[{entry['task_id']}]`" if entry.get("task_id") else ""
                ts = entry.get("timestamp", "")
                ts_str = f"`{ts}` " if ts else ""
                msg = entry["message"]
                if entry["level"] == "SUCCESS":
                    st.markdown(f"{ts_str}{level_icon}{tid_str} {msg}")
                elif entry["level"] == "ERROR":
                    st.error(f"{ts_str}{level_icon}{tid_str} {msg}")
                elif entry["level"] == "WARNING":
                    st.warning(f"{ts_str}{level_icon}{tid_str} {msg}")
                else:
                    st.caption(f"{ts_str}{level_icon}{tid_str} {msg}")
    else:
        st.info('暂无日志，点击「开始执行」查看调度过程')
