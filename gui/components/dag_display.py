"""DAG 可视化组件 - 用 NetworkX + Matplotlib 渲染任务依赖图"""

import platform
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import networkx as nx
import matplotlib.patches as mpatches

# 配置中文字体
if platform.system() == "Windows":
    for font_name in ["Microsoft YaHei", "SimHei", "KaiTi"]:
        for f in fm.fontManager.ttflist:
            if font_name in f.name:
                plt.rcParams["font.sans-serif"] = [f.name, "DejaVu Sans"]
                break
        else:
            continue
        break
    else:
        plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
else:
    plt.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei", "Noto Sans CJK SC", "DejaVu Sans"]

plt.rcParams["axes.unicode_minus"] = False

# Worker 对应图标
WORKER_ICON = {
    "retrieval_worker": "🔍",
    "data_worker": "🧹",
    "ml_worker": "🤖",
    "algorithm_worker": "⚙️",
    "security_worker": "🛡️",
    "code_worker": "💻",
    "network_worker": "🌐",
    "database_worker": "🗄️",
    "strategy_worker": "📊",
}

# 状态颜色映射
STATUS_COLORS = {
    "pending": "#4A90D9",
    "running": "#F5A623",
    "completed": "#7ED321",
    "failed": "#D0021B",
}

STATUS_LABELS = {
    "pending": "等待执行",
    "running": "执行中",
    "completed": "已完成",
    "failed": "失败",
}


def render_dag(adj: dict[str, dict], title: str = "任务依赖图 (DAG)"):
    if not adj:
        st.info("暂无任务依赖图")
        return

    G = nx.DiGraph()
    for tid, node in adj.items():
        status = node["data"].get("status", "pending")
        G.add_node(tid, status=status)
    for tid, node in adj.items():
        for next_id in node.get("next", []):
            G.add_edge(tid, next_id)

    fig, ax = plt.subplots(figsize=(9, 5))

    try:
        pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
    except Exception:
        pos = nx.spring_layout(G, seed=42, k=2)

    node_colors = [STATUS_COLORS.get(G.nodes[n].get("status", "pending"), "#4A90D9") for n in G.nodes]

    nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#888888", arrows=True,
                           arrowsize=18, width=1.5, connectionstyle="arc3,rad=0.05")

    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=2200,
                           edgecolors="#333333", linewidths=1.8)

    labels = {}
    for n in G.nodes:
        data = adj[n]["data"]
        task_type = data.get("task_type", "")
        worker_name = data.get("worker_name", "")
        desc = data.get("description", n)
        if len(desc) > 15:
            desc = desc[:13] + ".."
        # 节点标签: 任务ID + 任务类型 + 描述
        labels[n] = f"{n}\n{task_type}\n{desc}"

    nx.draw_networkx_labels(G, pos, ax=ax, labels=labels, font_size=7,
                            font_weight="bold", font_color="#1a1a1a")

    legend_patches = [
        mpatches.Patch(color=color, label=STATUS_LABELS[name])
        for name, color in STATUS_COLORS.items()
    ]
    ax.legend(handles=legend_patches, loc="lower right", fontsize=9, ncol=4,
              framealpha=0.9, edgecolor="#cccccc")

    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    ax.axis("off")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
