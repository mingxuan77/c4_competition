"""LangGraph 调度引擎 — 使用 LangChain + LangGraph 替换手写调度。

旧架构: IntentParser → TaskPlanner → DAGBuilder → Scheduler(Kahn+threading.Thread)
新架构: IntentParser(LangChain) → TaskPlanner → LangGraph(StateGraph自动并行)

LangGraph 自动处理：
- 并行：无依赖关系的节点 → 自动并行执行
- 串行：有依赖的节点 → 依次执行
- 汇聚：多个前置节点 → 全部完成后才执行
"""

import time
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from config import LLM_CONFIG, get_llm_client

# 导入内置工具包，触发 @tool 装饰器自动注册
import workers.tools.builtin  # noqa: F401


# ═══════════════════════════════════════════════════
# 1. State — LangGraph 节点间流转的状态
# ═══════════════════════════════════════════════════

def _merge_dicts(left: dict, right: dict) -> dict:
    """合并两个字典，right 覆盖 left 中同名 key（用于 results 累加）。"""
    merged = dict(left or {})
    merged.update(right or {})
    return merged


class AgentState(TypedDict):
    """每个 LangGraph 节点读取/写入此对象。"""
    tasks: list[dict]
    results: Annotated[dict, _merge_dicts]
    logs: Annotated[list[dict], lambda left, right: (left or []) + (right or [])]


# ═══════════════════════════════════════════════════
# 2. Worker → LangGraph 节点包装
# ═══════════════════════════════════════════════════

TASK_TYPE_MAP = {
    "retrieval":       ("retrieval_worker",  "数据检索", "🔍"),
    "data_processing": ("data_worker",       "数据处理", "🧹"),
    "ml_prediction":   ("ml_worker",         "机器学习", "🤖"),
    "algorithm":       ("algorithm_worker",  "算法优化", "⚙️"),
    "security":        ("security_worker",   "安全分析", "🛡️"),
    "code_execution":  ("code_worker",       "代码执行", "💻"),
    "network":         ("network_worker",    "网络监控", "🌐"),
    "database":        ("database_worker",   "数据库",   "🗄️"),
    "strategy":        ("strategy_worker",   "策略输出", "📊"),
    "report_export":   ("report_exporter",   "报告导出", "📄"),
    "http_request":        ("http_worker",       "HTTP调用", "🌐"),
    "production_monitor":  ("production_monitor",  "产线监控", "📡"),
    "production_adjuster": ("production_adjuster", "产线调整", "🔧"),
}

_workers_cache = None

def _get_workers():
    global _workers_cache
    if _workers_cache is None:
        from workers.algorithm_worker import AlgorithmWorker
        from workers.ml_worker import MLWorker
        from workers.retrieval_worker import RetrievalWorker, DataWorker
        from workers.security_worker import SecurityWorker
        from workers.code_executor import CodeWorker
        from workers.network_worker import NetworkWorker
        from workers.database_worker import DatabaseWorker
        from workers.strategy_worker import StrategyWorker
        from workers.report_exporter import ReportExporter
        from workers.http_worker import HTTPWorker
        from workers.production_monitor import ProductionMonitorWorker
        from workers.production_adjuster import ProductionAdjusterWorker
        _workers_cache = {
            "retrieval_worker": RetrievalWorker(),
            "data_worker": DataWorker(),
            "ml_worker": MLWorker(),
            "algorithm_worker": AlgorithmWorker(),
            "security_worker": SecurityWorker(),
            "code_worker": CodeWorker(),
            "network_worker": NetworkWorker(),
            "database_worker": DatabaseWorker(),
            "strategy_worker": StrategyWorker(),
            "report_exporter": ReportExporter(),
            "http_worker": HTTPWorker(),
            "production_monitor": ProductionMonitorWorker(),
            "production_adjuster": ProductionAdjusterWorker(),
        }
    return _workers_cache


def _make_node(task: dict):
    """为每个任务创建一个 LangGraph 节点函数。"""
    tid = task["task_id"]
    task_type = task["task_type"]
    worker_name, type_label, icon = TASK_TYPE_MAP.get(task_type, ("algorithm_worker", task_type, ""))

    def node(state: AgentState) -> dict:
        workers = _get_workers()
        worker = workers.get(worker_name)

        log_start = {
            "timestamp": time.strftime("%H:%M:%S"), "level": "INFO",
            "message": f"{icon} [{type_label}] {worker_name} 执行: {task.get('description', tid)[:40]}",
            "task_id": tid,
        }

        if not worker:
            return {
                "results": {tid: {"status": "skipped", "result": {"output": "无可用Worker"},
                                  "worker_name": "-", "type_label": type_label}},
                "logs": [log_start],
            }

        try:
            # 将上游任务的结果注入到当前任务，让下游Agent能引用前面的分析
            task_with_context = dict(task)
            task_with_context.setdefault("params", {})
            upstream = {}
            for dep_id in task.get("deps", []):
                dep_result = state["results"].get(dep_id, {})
                if dep_result.get("status") == "success":
                    upstream[dep_id] = dep_result.get("result", {})
            task_with_context["params"]["upstream_results"] = upstream

            result = worker.execute(task_with_context)
            return {
                "results": {tid: {"status": "success", "result": result,
                                  "worker_name": worker_name, "type_label": type_label}},
                "logs": [log_start, {
                    "timestamp": time.strftime("%H:%M:%S"), "level": "SUCCESS",
                    "message": f"✅ [{type_label}] 完成", "task_id": tid,
                }],
            }
        except Exception as e:
            return {
                "results": {tid: {"status": "failed", "result": {"output": str(e)},
                                  "worker_name": worker_name, "type_label": type_label}},
                "logs": [log_start, {
                    "timestamp": time.strftime("%H:%M:%S"), "level": "ERROR",
                    "message": f"❌ 失败: {e}", "task_id": tid,
                }],
            }

    node.__name__ = f"worker_{tid}"
    return node


# ═══════════════════════════════════════════════════
# 3. 图构建 — 动态生成 LangGraph StateGraph
# ═══════════════════════════════════════════════════

def build_graph(tasks: list[dict]) -> StateGraph:
    """根据任务列表动态构建 LangGraph 执行图。

    关键：LangGraph 自动根据边的关系判断并行/串行。
    - 节点有多个出边指向不同节点 → 那些节点自动并行
    - 多个入边汇聚到一个节点 → 该节点等待所有前置完成

    示例:
      A（无依赖）、B（依赖A）、C（依赖A）
      → A 先执行 → B、C 自动并行 → 完毕

      START ─→ A ─→ B ─→ END
                └→ C ─┘
    """
    g = StateGraph(AgentState)

    # 添加节点
    for task in tasks:
        g.add_node(task["task_id"], _make_node(task))

    # 添加边：无依赖的任务从 START 出发
    for task in tasks:
        if not task.get("deps"):
            g.add_edge(START, task["task_id"])

    # 添加边：有依赖的任务从其前置任务连过来
    for task in tasks:
        for dep_id in task.get("deps", []):
            g.add_edge(dep_id, task["task_id"])

    # 所有任务 → END（LangGraph 知道当某节点全部出边都可达 END 时结束）
    # 找到所有没有后继的任务（出度为0的节点）→ 连到 END
    has_successor = set()
    for task in tasks:
        for dep_id in task.get("deps", []):
            has_successor.add(dep_id)

    for task in tasks:
        if task["task_id"] not in has_successor:
            g.add_edge(task["task_id"], END)

    return g


# ═══════════════════════════════════════════════════
# 4. 主入口 — app.py 调用此函数
# ═══════════════════════════════════════════════════

def run_with_langgraph(tasks: list[dict], user_input: str = "") -> dict:
    """使用 LangGraph 执行任务列表。

    Args:
        tasks: TaskPlanner.plan() 的输出（标准化任务列表）
        user_input: 原始用户输入（用于日志）

    Returns:
        {"results": {task_id: {...}}, "logs": [...]}
    """
    g = build_graph(tasks)
    compiled = g.compile()  # LangGraph 编译图（检查合法性、优化执行计划）

    initial_state: AgentState = {
        "tasks": tasks,
        "results": {},
        "logs": [{
            "timestamp": time.strftime("%H:%M:%S"), "level": "INFO",
            "message": f"🚀 [LangGraph] 启动 — {len(tasks)} 个节点，并行能力自动识别",
            "task_id": None,
        }],
    }

    final_state = compiled.invoke(initial_state)

    total = len(final_state.get("results", {}))
    success = sum(1 for r in final_state.get("results", {}).values() if r.get("status") == "success")
    final_state["logs"].append({
        "timestamp": time.strftime("%H:%M:%S"), "level": "SUCCESS",
        "message": f"✅ [LangGraph] 全流程完成 ({success}/{total} 成功)",
        "task_id": None,
    })

    return {
        "results": final_state.get("results", {}),
        "logs": final_state.get("logs", []),
    }


# ═══════════════════════════════════════════════════
# 5. LangChain 意图解析（使用 structured output）
# ═══════════════════════════════════════════════════

def parse_intent_with_langchain(user_input: str) -> dict:
    """使用 LangChain with_structured_output 进行意图解析。

    相比手写 JSON 解析更可靠：LangChain 利用 function calling
    机制确保 LLM 输出始终符合预期 schema。
    """
    client = get_llm_client()
    if not client:
        return None  # 返回 None 表示让调用方用规则匹配

    llm = ChatOpenAI(
        api_key=LLM_CONFIG["api_key"],
        base_url=LLM_CONFIG["base_url"],
        model=LLM_CONFIG["model"],
        temperature=0.3,
    )

    schema = {
        "title": "task_pipeline",
        "type": "object",
        "properties": {
            "intent": {"type": "string", "description": "一句话总结用户意图"},
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "type": {"type": "string", "enum": list(TASK_TYPE_MAP.keys())},
                        "description": {"type": "string"},
                    },
                    "required": ["task_id", "type", "description"],
                },
            },
            "dependencies": {
                "type": "object",
                "additionalProperties": {"type": "array", "items": {"type": "string"}},
            },
        },
        "required": ["intent", "tasks"],
    }

    system_prompt = """你是一个多智能体协同调度系统的任务拆解器。根据用户需求，输出结构化任务流水线。

可用任务类型:
- retrieval:          数据检索(搜索/获取/查询数据/收集信息)
- data_processing:     数据处理(清洗/ETL/分类汇总/特征工程)
- ml_prediction:       机器学习(预测/分类/回归/趋势分析)
- algorithm:           算法优化(匹配/排序/投资组合/路径规划)
- security:            安全分析(漏洞扫描/风险评估/合规)
- code_execution:      代码执行(沙箱)
- network:             网络监控(拓扑/流量)
- database:            数据库(查询优化/迁移)
- strategy:            策略输出(综合建议/报告)
- production_monitor:  产线监控(读取仿真数据/检测异常/趋势分析)
- production_adjuster: 产线调整(计算调整量/执行工艺参数修改)

规则:
1. task_id 必须用单大写字母: A, B, C, D, E, F
2. dependencies 中每个键指向其前置任务列表，如 {"B": ["A"], "C": ["A","B"]}
3. 最后一步必须是 strategy 类型
4. 任务3-6个
5. 相似的任务合并为一个(如"检索A数据"+"检索B数据"合并为"检索相关数据")
6. 必须有 dependencies 字段，即使为空也写 {}
7. 半导体产线相关任务优先使用 production_monitor 和 production_adjuster
"""
    try:
        structured_llm = llm.with_structured_output(schema, method="function_calling")
        result = structured_llm.invoke(
            system_prompt + f"\n\n请解析：{user_input}"
        )
        deps = result.get("dependencies", {})
        tasks = []
        for t in result["tasks"]:
            tasks.append({
                "task_id": t["task_id"],
                "task_type": t["type"],
                "description": t.get("description", ""),
                "deps": deps.get(t["task_id"], []),
                "params": {},
            })

        # 确保最后有 report_export 任务（生成可下载文件）
        has_export = any(t["task_type"] == "report_export" for t in tasks)
        has_strategy = any(t["task_type"] == "strategy" for t in tasks)
        if not has_export:
            last_id = max((t["task_id"] for t in tasks), key=lambda x: ord(x[0]) if x else 0)
            next_id = chr(ord(last_id) + 1) if last_id else "F"
            export_deps = [last_id]
            tasks.append({
                "task_id": next_id,
                "task_type": "report_export",
                "description": "将分析结果导出为Word/Excel/PDF报告文件",
                "deps": export_deps,
                "params": {"title": result.get("intent", "分析报告")},
            })

        return {"intent": result["intent"], "tasks": tasks}
    except Exception as e:
        return None  # 失败 → 回退规则匹配
