"""结果面板 - 展示各 Worker 执行结果和最终策略报告"""

import json
import copy
import streamlit as st
import pandas as pd


def render_result_panel(results: dict[str, dict], tasks: list[dict] | None = None):
    if not results:
        return

    # ─── 先提取策略报告，作为最终输出在最前面展示 ───
    strategy_data = None
    strategy_task_id = None
    sorted_ids = sorted(results.keys())
    for tid in sorted_ids:
        r = results[tid]
        if r.get("status") == "success":
            rd = r.get("result", {})
            if isinstance(rd, dict) and "strategy" in rd:
                strategy_data = rd["strategy"]
                strategy_task_id = tid
                break

    # ─── 最终策略报告 ───
    if strategy_data:
        st.markdown("## 📊 最终分析报告")
        st.markdown("---")

        # 报告标题
        st.markdown(f"### {strategy_data.get('title', '')}")
        st.caption(f"{strategy_data.get('subtitle', '')}")
        st.caption(f"🤖 {strategy_data.get('generated_by', '')}")

        # 执行摘要
        st.info(strategy_data.get("executive_summary", ""))

        # 分析结果
        ar = strategy_data.get("analysis_results", {})
        if ar:
            st.markdown("#### 🔬 各维度分析结果")
            tabs = st.tabs(list(ar.keys()))
            for tab, (key, val) in zip(tabs, ar.items()):
                with tab:
                    if isinstance(val, dict):
                        for k, v in val.items():
                            if isinstance(v, list):
                                st.markdown(f"**{k}:**")
                                for item in v:
                                    st.markdown(f"- {item}")
                            else:
                                st.markdown(f"**{k}:** {v}")

        # 策略建议
        st.markdown("#### 🎯 策略建议清单")
        recs = strategy_data.get("recommendations", [])
        if recs:
            rec_rows = []
            for rec in recs:
                rec_rows.append({
                    "优先级": rec.get("priority", ""),
                    "行动方案": rec.get("action", ""),
                    "依据": rec.get("rationale", ""),
                    "预期效果": rec.get("estimated_impact", ""),
                    "时间线": rec.get("timeline", ""),
                    "负责方": rec.get("responsible", ""),
                })
            st.dataframe(pd.DataFrame(rec_rows), use_container_width=True, hide_index=True)

        # 风险 + KPI + 时间线 三列
        st.markdown("#### ⚡ 风险评估 & KPI指标 & 实施时间线")
        c1, c2, c3 = st.columns(3)

        with c1:
            risk = strategy_data.get("risk_assessment", {})
            st.markdown(f"**整体风险等级:** `{risk.get('overall_risk_level', '-')}`")
            for rk in risk.get("key_risks", []):
                st.markdown(f"- ⚠️ {rk}")
            st.caption(f"*缓解: {risk.get('mitigation', '')}*")

        with c2:
            kpis = strategy_data.get("kpi_targets", {})
            for k, v in kpis.items():
                st.metric(k, v)

        with c3:
            timeline = strategy_data.get("timeline", {})
            for time, action in timeline.items():
                st.markdown(f"**{time}:** {action}")

        # 结论
        st.markdown("---")
        st.success(strategy_data.get("conclusion", ""))

    # ─── 执行摘要统计 ───
    st.markdown("---")
    st.markdown("## 📋 执行详情")
    total = len(results)
    success_count = sum(1 for r in results.values() if r.get("status") == "success")
    failed_count = sum(1 for r in results.values() if r.get("status") == "failed")
    col1, col2, col3 = st.columns(3)
    col1.metric("总任务数", total)
    col2.metric("成功", success_count, delta=None if success_count == total else f"-{total - success_count}")
    col3.metric("失败", failed_count, delta_color="inverse" if failed_count > 0 else "off")

    # ─── 子Agent分配明细 ───
    st.markdown("### 📌 子Agent任务分配明细")
    rows = []
    for tid in sorted_ids:
        r = results[tid]
        status = "✅" if r.get("status") == "success" else "❌" if r.get("status") == "failed" else "⏭️"
        desc = ""
        if tasks:
            for t in tasks:
                if t["task_id"] == tid:
                    desc = t.get("description", "")
                    break
        rows.append({
            "任务": f"{status} {tid}",
            "子Agent": r.get("worker_name", "-"),
            "类型": r.get("type_label", "-"),
            "工作内容": desc[:50] + (".." if len(desc) > 50 else ""),
            "结果": "成功" if r.get("status") == "success" else r.get("status", "-"),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ─── 各子Agent详细输出（折叠） ───
    st.markdown("### 🔍 各子Agent详细输出")
    for tid in sorted_ids:
        r = results[tid]
        if r.get("status") != "success":
            continue
        # 跳过策略任务（已在上方完整展示）
        if strategy_task_id and tid == strategy_task_id:
            continue

        result_data = copy.deepcopy(r.get("result", {}))
        type_label = r.get("type_label", "")
        worker_name = r.get("worker_name", "")

        with st.expander(f"✅ 任务 {tid} — {type_label} ({worker_name})", expanded=False):
            if not isinstance(result_data, dict):
                st.text(str(result_data))
                continue

            output = result_data.pop("output", "")
            if output:
                st.success(output)

            # 安全报告
            if "scan_report" in result_data:
                sr = result_data["scan_report"]
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("漏洞总数", sr.get("total_vulnerabilities", 0))
                c2.metric("严重", sr.get("critical", 0), delta_color="inverse")
                c3.metric("高危", sr.get("high", 0), delta_color="inverse")
                c4.metric("合规评分", f"{sr.get('compliance_score', 0)}/100")
                if sr.get("top_issues"):
                    st.caption("TOP 风险:")
                    for iss in sr["top_issues"]:
                        st.caption(f"  🔴 {iss}")

            # 网络分析
            elif "network_analysis" in result_data:
                na = result_data["network_analysis"]
                c1, c2, c3 = st.columns(3)
                c1.metric("网络节点", na.get("total_nodes", 0))
                c2.metric("带宽利用率", na.get("bandwidth_utilization", "-"))
                c3.metric("P95延迟", f"{na.get('latency_p95_ms', 0)}ms")
                if na.get("anomalies_detected"):
                    for a in na["anomalies_detected"]:
                        st.warning(f"🚨 {a}")
                if na.get("bottlenecks"):
                    st.caption("瓶颈:")
                    for b in na["bottlenecks"]:
                        st.caption(f"  ⚠️ {b}")

            # ML结果
            elif "model" in result_data:
                m = result_data["model"]
                c1, c2, c3 = st.columns(3)
                c1.metric("模型", m.get("type", "-"))
                c2.metric("R²", m.get("r2_score", "-"))
                c3.metric("Loss", m.get("final_loss", "-"))

            # 算法结果
            elif "algorithm_used" in result_data:
                st.info(f"算法: {result_data['algorithm_used']}")
                metrics = result_data.get("metrics", {})
                if metrics:
                    for k, v in metrics.items():
                        st.caption(f"  {k}: {v}")

            # DB结果
            elif "db_operations" in result_data:
                db = result_data["db_operations"]
                st.info(f"引擎: {db.get('engine', '')} | 处理行数: {db.get('rows_processed', 0):,} | "
                        f"查询数: {db.get('queries_executed', 0)}")

            # 检索结果
            elif "data_source" in result_data:
                st.info(f"数据源: {result_data['data_source']} | 规模: {result_data.get('data_size', '')}")
                if "sample" in result_data:
                    st.dataframe(pd.DataFrame(result_data["sample"]), use_container_width=True)

            # 报告导出
            elif "stats_table" in result_data:
                stbl = result_data["stats_table"]
                st.markdown("**📊 统计表格:**")
                st.dataframe(
                    pd.DataFrame(stbl["rows"], columns=stbl["columns"]),
                    use_container_width=True, hide_index=True,
                )
                pdf_meta = result_data.get("pdf_export", {})
                if pdf_meta:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("PDF页数", f"{pdf_meta.get('pages', 0)} 页")
                    c2.metric("文件大小", f"{pdf_meta.get('size_kb', 0)} KB")
                    c3.metric("章节数", len(pdf_meta.get("sections", [])))
                    if pdf_meta.get("sections"):
                        st.caption("PDF 章节: " + " → ".join(pdf_meta["sections"]))
                if "markdown_report" in result_data:
                    with st.expander("📝 Markdown 报告预览"):
                        st.code(result_data["markdown_report"], language="markdown")
                if "html_report" in result_data:
                    with st.expander("🌐 HTML 报告预览"):
                        st.code(result_data["html_report"], language="html")

            # 其他以JSON展示
            remaining = {k: v for k, v in result_data.items()
                        if k not in ("strategy", "scan_report", "network_analysis",
                                     "model", "algorithm_used", "metrics",
                                     "db_operations", "data_source", "data_size", "sample")}
            if remaining:
                st.code(json.dumps(remaining, ensure_ascii=False, indent=2), language="json")
