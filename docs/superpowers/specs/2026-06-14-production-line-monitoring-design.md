# 跨域分布式多智能体协同调度系统 — 详细设计文档

**版本**: v2.0 — 半导体产线智能监控与决策场景
**日期**: 2026-06-14
**状态**: 设计完成，待实现
**赛项**: 2026-B-EP1 智能体互联网创新攻关赛项

---

## 目录

- [第一章 项目概述](#第一章--项目概述)
- [第二章 系统架构总览](#第二章--系统架构总览)
- [第三章 核心流程详解](#第三章--核心流程详解)
- [第四章 Worker体系详解](#第四章--worker体系详解)
- [第五章 对话与记忆系统](#第五章--对话与记忆系统)
- [第六章 产线仿真引擎](#第六章--产线仿真引擎)
- [第七章 产线监控仪表盘](#第七章--产线监控仪表盘)
- [第八章 对话-监控联动与双模式设计](#第八章--对话-监控联动与双模式设计)
- [第九章 技术栈与部署](#第九章--技术栈与部署)
- [第十章 关键代码设计](#第十章--关键代码设计)

---

## 第一章  项目概述

### 1.1 项目背景与目标

本项目为2026年C4网络技术挑战赛（选拔赛）参赛作品，赛项编号2026-B-EP1「智能体互联网创新攻关赛项」。

**核心命题**：如何让多个不同领域的AI Agent协同工作，共同完成复杂的工业场景分析任务？

**场景定位**：半导体制造 — 聚焦良率关键路径（光刻 → 刻蚀 → 测试），通过多智能体协同实现产线状态检测、异常诊断、工艺参数智能调整和综合决策报告生成。半导体行业具有真实的痛点：良率波动造成巨额损失、设备宕机影响产能、工艺参数漂移难以实时捕捉。本系统通过模拟三条核心产线的运行数据，展示多智能体系统在工业场景中的实用价值。

**解决方案**：构建一个 Meta-Agent（元智能体），它不直接执行具体工作，而是像工厂的"智能调度中心"一样：理解需求 → 拆解任务 → 分配Agent → 协调执行 → 汇总报告。

### 1.2 核心概念

#### Meta-Agent（元智能体）

Meta-Agent 是系统的「大脑」，负责接收用户自然语言输入，经过意图解析、任务规划、DAG构建、调度执行四个步骤，最终产出结构化的分析报告。Meta-Agent 本身不执行任何具体分析工作，它的职责是「编排」而非「执行」。

#### Worker Agent（工作智能体）

Worker 是执行具体任务的专业Agent。系统内置12个Worker，覆盖数据检索、数据处理、机器学习、算法优化、安全分析、网络监控、数据库操作、代码执行、策略输出、报告导出、**产线监控**、**产线调整**等领域。每个Worker可以独立运行，也可以被Meta-Agent调度协同工作。

#### DAG 调度（有向无环图调度）

任务之间往往存在依赖关系。这些依赖构成一个有向无环图(DAG)。系统基于LangGraph自动识别哪些任务可以并行执行，哪些必须串行等待。

#### 产线仿真引擎

系统内置半导体产线仿真器，模拟光刻、刻蚀、测试三条产线的实时运行数据（产能、良率、设备OEE、工艺参数、缺陷率等），并支持异常事件注入（良率突降、设备告警、工艺漂移、WIP堆积）和参数动态调整。

### 1.3 系统能力一览

- **自然语言输入**：用户用日常语言描述需求，无需学习任何DSL或API
- **智能意图解析**：自动识别用户意图，拆解为子任务，构建依赖关系
- **并行任务调度**：基于LangGraph StateGraph，自动识别并行/串行执行
- **多Agent协同**：12个专业Worker各司其职，LLM模式下每个Worker调用大模型生成专业分析
- **产线实时仿真**：3条半导体产线独立仿真，数据每秒更新，支持异常注入
- **可视化监控仪表盘**：独立的监控Tab页，实时图表展示产线指标、趋势和调整日志
- **双模式运行**：自动检测调整（轻量级循环）+ 手动对话触发（全流程深度分析）
- **对话-监控联动**：产线异常自动推送至聊天，聊天中的调整实时反映在监控图表
- **完整策略报告**：自动聚合所有Worker输出，生成含诊断、建议、风险评估的完整报告
- **文件导出**：支持Word/Excel/PDF格式报告下载

---

## 第二章  系统架构总览

### 2.1 四层架构（新增仿真层）

系统采用四层架构：用户交互层 → 调度编排层 → 执行层 → 仿真数据层。每层职责分明，通过标准化的数据结构（st.session_state共享总线）传递信息。

```
┌──────────────────────────────────────────────────────────┐
│  用户交互层 (Streamlit UI)                                │
│  ┌────────────────────┬──────────────────────────────┐   │
│  │  Tab1: 智能对话     │  Tab2: 产线监控仪表盘         │   │
│  │  - 聊天界面         │  - 3条产线指标卡片            │   │
│  │  - 工作流状态面板   │  - 良率/产能趋势图            │   │
│  │  - 报告下载区       │  - Agent调整日志流            │   │
│  │                    │  - 自动检测控制栏              │   │
│  └────────────────────┴──────────────────────────────┘   │
├──────────────────────────────────────────────────────────┤
│  调度编排层 (Meta-Agent)                                  │
│  IntentParser → LangGraph Engine → TaskPlanner            │
│  - LLM意图解析 (LangChain structured output)              │
│  - LangGraph StateGraph 并行调度                          │
│  - Worker 选择与结果聚合                                  │
├──────────────────────────────────────────────────────────┤
│  执行层 (Workers)                                         │
│  原有10个Worker + 新增2个Worker                            │
│  retrieval, data_processing, ml_prediction, algorithm,    │
│  security, code_execution, network, database, strategy,   │
│  report_export, production_monitor, production_adjuster   │
├──────────────────────────────────────────────────────────┤
│  仿真数据层 (Simulation)                                   │
│  SemiconductorSimulator (独立线程)                         │
│  - 光刻线仿真 (LithoSimulator)                            │
│  - 刻蚀线仿真 (EtchSimulator)                             │
│  - 测试线仿真 (TestSimulator)                             │
│  - 异常事件注入引擎                                        │
│  - 参数调整响应接口                                        │
└──────────────────────────────────────────────────────────┘
```

### 2.2 数据流向

```
用户输入"光刻线良率异常，帮我分析"
    → IntentParser 识别为"产线状态检测"意图
    → LangGraph 构建并行DAG:
        A: production_monitor (读取仿真数据)
        B: data_processing (趋势分析) ← 依赖A
        C: strategy (综合诊断报告) ← 依赖B
        D: report_export (导出报告) ← 依赖C
    → 各Worker执行，结果回传
    → build_workflow_response 拼装报告卡片
    → 聊天框展示 + 仿真参数(如有调整)实时影响Tab2图表
```

调整路径：
```
用户"调整曝光剂量+2"
    → IntentParser → Adjuster Worker → 调用 simulation.apply_adjustment()
    → 仿真器响应 → Tab2图表出现调整标记 → 良率曲线逐步回升
```

### 2.3 目录结构与模块职责

```
c4_competion/
├── app.py                      # Streamlit 主入口（多Tab布局）
├── config.py                   # LLM + 仿真参数配置
├── requirements.txt            # 依赖清单
│
├── meta_agent/                 # 调度编排层
│   ├── __init__.py
│   ├── intent_parser.py        # 意图解析（规则+LLM双模式，新增产线模板）
│   ├── task_planner.py         # 任务标准化
│   ├── langgraph_engine.py     # LangGraph调度引擎（注册新Worker）
│   ├── dag_builder.py          # DAG构建（保留作为回退）
│   ├── scheduler.py            # 旧调度器（保留作为回退）
│   └── chat_llm.py             # 多轮对话管理
│
├── workers/                    # 执行层
│   ├── __init__.py
│   ├── base_worker.py          # Worker基类（_call_llm + _call_tool + _simulate）
│   ├── retrieval_worker.py     # 数据检索
│   ├── algorithm_worker.py     # 算法优化
│   ├── ml_worker.py            # 机器学习
│   ├── security_worker.py      # 安全分析
│   ├── code_executor.py        # 代码执行（沙箱）
│   ├── network_worker.py       # 网络监控
│   ├── database_worker.py      # 数据库操作
│   ├── strategy_worker.py      # 策略输出（更新prompt模板）
│   ├── report_exporter.py      # 报告导出（Word/Excel/PDF）
│   ├── http_worker.py          # HTTP调用
│   ├── production_monitor.py   # [新增] 产线监控Worker
│   ├── production_adjuster.py  # [新增] 产线调整Worker
│   └── tools/                  # 工具注册中心
│       ├── __init__.py
│       ├── registry.py
│       ├── schema.py
│       ├── tools.yaml
│       └── builtin/
│           ├── __init__.py
│           ├── file_export.py
│           ├── sandbox.py
│           └── http_client.py
│
├── simulation/                 # [新增] 仿真数据层
│   ├── __init__.py
│   ├── semiconductor_sim.py    # 半导体产线仿真核心
│   └── production_line.py      # 单条产线状态机
│
├── utils/
│   ├── __init__.py
│   ├── graph_utils.py
│   └── logger.py
│
├── gui/                        # UI组件（保留）
│   ├── __init__.py
│   └── components/
│       ├── dag_display.py
│       ├── input_panel.py
│       ├── result_panel.py
│       └── status_panel.py
│
└── outputs/                    # 报告文件输出目录
```

---

## 第三章  核心流程详解

本章追踪一个完整的请求从用户输入到最终报告的全过程。

**以用户输入「光刻线良率异常，帮我分析原因并调整工艺参数」为例。**

### 3.1 第一步：意图解析 (IntentParser)

职责：将用户的自然语言输入转化为结构化的意图描述和任务列表。

#### 3.1.1 两种工作模式

1) **规则匹配模式**（默认/Mock模式）：基于关键词匹配和预设模板，零API依赖
2) **LLM解析模式**（需配置API Key）：调用DeepSeek API通过LangChain structured output进行语义理解

#### 3.1.2 预设模板（更新后）

系统内置8个预设模板，覆盖半导体产线监控核心场景：

| 模板名称 | 触发关键词 | 任务链 |
|---------|-----------|--------|
| **产线状态检测** | 检测、状态、指标、异常、良率、产能 | Monitor→Data→Strategy→Export |
| **产线自动调整** | 调整、优化、补偿、修改参数 | Monitor→ML→Adjuster→Strategy→Export |
| **产线综合分析** | 综合、全面、分析报告、瓶颈 | Monitor→Data→ML→Strategy→Export |
| **设备故障诊断** | 故障、宕机、OEE、报警 | Monitor→Algorithm→Strategy→Export |
| **良率根因分析** | 良率下降、原因、根因 | Monitor→Data→ML→Adjuster→Strategy→Export |
| **数据中心安全运维** | 安全、漏洞、扫描、拓扑、运维 | Network→Security→Data→Algorithm→Strategy |
| **智能路由优化** | 路由、网络、拓扑、负载均衡 | Network→Data→Algorithm→Strategy |
| **数据库迁移** | 数据库、迁移、SQL、查询优化 | Database→Data→Code→Network→Strategy |

新增的核心模板：

```python
"产线状态检测": {
    "intent": "半导体产线状态检测与异常诊断",
    "tasks": [
        {"task_id": "A", "type": "production_monitor",
         "description": "读取光刻/刻蚀/测试三条产线当前指标和历史趋势"},
        {"task_id": "B", "type": "data_processing",
         "description": "分析异常趋势：良率下降斜率、OEE波动模式、DPPM变化"},
        {"task_id": "C", "type": "strategy",
         "description": "综合诊断报告：异常产线识别、根因推断、行动建议"},
        {"task_id": "D", "type": "report_export",
         "description": "导出检测报告(Word/Excel/PDF)"},
    ],
    "dependencies": {"B": ["A"], "C": ["B"], "D": ["C"]},
},

"产线自动调整": {
    "intent": "半导体产线工艺参数智能调整",
    "tasks": [
        {"task_id": "A", "type": "production_monitor",
         "description": "拉取目标产线近30分钟历史数据"},
        {"task_id": "B", "type": "ml_prediction",
         "description": "预测继续漂移的后果（良率预期跌至多少）"},
        {"task_id": "C", "type": "production_adjuster",
         "description": "计算最优调整参数并写入仿真器执行"},
        {"task_id": "D", "type": "strategy",
         "description": "调整效果评估与后续建议"},
        {"task_id": "E", "type": "report_export",
         "description": "导出调整报告(Word/Excel/PDF)"},
    ],
    "dependencies": {"B": ["A"], "C": ["B"], "D": ["C"], "E": ["D"]},
},

"产线综合分析": {
    "intent": "半导体产线综合运行分析与瓶颈诊断",
    "tasks": [
        {"task_id": "A", "type": "production_monitor",
         "description": "全量采集三条产线运行数据和事件日志"},
        {"task_id": "B", "type": "data_processing",
         "description": "数据清洗与趋势分析：良率相关性、OEE瓶颈识别"},
        {"task_id": "C", "type": "ml_prediction",
         "description": "预测未来4小时良率和产能趋势"},
        {"task_id": "D", "type": "strategy",
         "description": "综合决策报告：瓶颈排序、调整优先级、PM建议"},
        {"task_id": "E", "type": "report_export",
         "description": "导出综合分析报告(Word/Excel/PDF)"},
    ],
    "dependencies": {"B": ["A"], "C": ["B"], "D": ["C"], "E": ["D"]},
},
```

#### 3.1.3 意图解析输出

无论哪种模式，意图解析的输出结构是统一的：

```json
{
    "intent": "半导体产线状态检测与异常诊断",
    "tasks": [...],
    "dependencies": {"B": ["A"], "C": ["B"], "D": ["C"]}
}
```

### 3.2 第二步：任务规划 (TaskPlanner)

将意图解析结果标准化为LangGraph可执行的任务列表。每个任务包含task_id、task_type、description、deps、params。

### 3.3 第三步：LangGraph 并行调度

系统使用LangGraph StateGraph替代手写Kahn算法调度。关键优势：

- **自动并行**：无依赖关系的节点→自动并行执行
- **自动串行**：有依赖的节点→依次执行
- **自动汇聚**：多个前置节点→全部完成后才执行

```
例：产线状态检测模板的DAG
START ─→ A(Monitor) ─→ B(Data) ─→ C(Strategy) ─→ D(Export) ─→ END
```

```
例：产线自动调整模板的DAG
START ─→ A(Monitor) ─→ B(ML) ─→ C(Adjuster) ─→ D(Strategy) ─→ E(Export) ─→ END
```

### 3.4 第四步：结果聚合

将所有Worker的执行结果聚合成自然语言式的分析报告卡片，在聊天框展示。

### 3.5 Worker选择机制

调度器通过 TASK_TYPE_MAP 将任务类型映射到具体的Worker实例：

```python
TASK_TYPE_MAP = {
    "retrieval":           ("retrieval_worker",      "数据检索", "🔍"),
    "data_processing":     ("data_worker",           "数据处理", "🧹"),
    "ml_prediction":       ("ml_worker",             "机器学习", "🤖"),
    "algorithm":           ("algorithm_worker",      "算法优化", "⚙️"),
    "security":            ("security_worker",       "安全分析", "🛡️"),
    "code_execution":      ("code_worker",           "代码执行", "💻"),
    "network":             ("network_worker",        "网络监控", "🌐"),
    "database":            ("database_worker",       "数据库",   "🗄️"),
    "strategy":            ("strategy_worker",       "策略输出", "📊"),
    "report_export":       ("report_exporter",       "报告导出", "📄"),
    "http_request":        ("http_worker",           "HTTP调用", "🌐"),
    "production_monitor":  ("production_monitor",    "产线监控", "📡"),  # 新增
    "production_adjuster": ("production_adjuster",   "产线调整", "🔧"),  # 新增
}
```

---

## 第四章  Worker体系详解

### 4.1 Worker基类设计

所有Worker继承自 BaseWorker 抽象类，获得三个核心能力：

- `_simulate_work(description)`: 模拟工作延迟（0.3~1.0秒随机），用于离线演示模式
- `_call_llm(system_prompt, user_prompt)`: 调用LLM生成专业分析，LLM不可用时返回None
- `_call_tool(tool_name, **kwargs)`: 调用ToolRegistry中注册的工具

### 4.2 双模式执行策略

每个Worker的execute()方法都遵循统一的「LLM优先、模拟兜底」策略。

### 4.3 新增Worker：产线监控 Worker

**位置**: `workers/production_monitor.py`
**职责**: 从仿真引擎读取三条产线的实时数据，生成结构化摘要和初步诊断。

```python
class ProductionMonitorWorker(BaseWorker):
    """产线监控 Worker — 读取仿真数据 + 趋势摘要 + 异常检测"""

    def execute(self, task: dict) -> dict:
        # 从 st.session_state 注入的仿真数据中读取
        sim_snapshot = task.get("params", {}).get("simulation_snapshot", {})
        history = task.get("params", {}).get("simulation_history", [])

        # 构建结构化摘要
        summary_lines = ["## 当前产线状态\n"]
        for line_id, data in sim_snapshot.items():
            name = data.get("name", line_id)
            status = data.get("status", "unknown")
            summary_lines.append(
                f"### {name}\n"
                f"- 状态: {status}\n"
                f"- 产能: {data.get('output', '-')} wph\n"
                f"- 良率: {data.get('yield_rate', 0)*100:.1f}%\n"
                f"- OEE: {data.get('oee', 0)*100:.1f}%\n"
            )

        # 异常检测
        alerts = self._detect_alerts(sim_snapshot)

        # 调用LLM做初步诊断
        llm_output = self._call_llm(
            system_prompt=(
                "你是半导体产线监控专家。请根据产线实时数据给出初步诊断意见。"
                "要求：1)识别每条产线的健康状态 2)指出异常指标的潜在根因"
                "3)建议是否需要人工干预 4)输出500-1000字"
            ),
            user_prompt="\n".join(summary_lines) + "\n\n异常检测结果:\n" +
                        "\n".join(f"- ⚠️ {a}" for a in alerts)
        )

        return {
            "output": llm_output or "\n".join(summary_lines),
            "raw_metrics": {
                line_id: {
                    "yield": data["yield_rate"],
                    "oee": data["oee"],
                    "output": data.get("output"),
                    "status": data.get("status"),
                }
                for line_id, data in sim_snapshot.items()
            },
            "alerts": alerts,
        }

    def _detect_alerts(self, sim_data: dict) -> list[str]:
        """阈值检测"""
        alerts = []
        for line_id, data in sim_data.items():
            if data.get("yield_rate", 1) < 0.93:
                alerts.append(f"[{line_id}] 良率偏低 ({data['yield_rate']*100:.1f}%)")
            if data.get("oee", 1) < 0.60:
                alerts.append(f"[{line_id}] OEE告警 ({data['oee']*100:.1f}%)")
            if line_id == "test" and data.get("dppm", 0) > 600:
                alerts.append(f"[{line_id}] DPPM超标 ({data['dppm']})")
        return alerts
```

### 4.4 新增Worker：产线调整 Worker

**位置**: `workers/production_adjuster.py`
**职责**: 分析上游Worker的诊断结果，计算最优调整参数，通过仿真引擎接口执行调整。

```python
class ProductionAdjusterWorker(BaseWorker):
    """产线调整 Worker — 计算调整量并写入仿真器"""

    def execute(self, task: dict) -> dict:
        upstream = task.get("params", {}).get("upstream_results", {})
        sim_snapshot = task.get("params", {}).get("simulation_snapshot", {})
        target_line = task.get("params", {}).get("target_line", "auto")

        # 从上游提取告警和诊断
        alerts = []
        for uid, r in upstream.items():
            if isinstance(r, dict):
                alerts.extend(r.get("alerts", []))

        # 调用LLM计算调整方案
        llm_result = self._call_llm(
            system_prompt=(
                "你是半导体工艺工程师。根据产线异常数据，给出具体可量化的工艺参数调整方案。\n"
                "可调参数：\n"
                "- 光刻线: exposure_dose (mJ/cm², 范围20-30), focus_offset (nm, 范围0-50)\n"
                "- 刻蚀线: rf_power (W, 范围400-600), chamber_pressure (mTorr, 范围20-50)\n"
                "- 测试线: sampling_rate (%, 范围50-100)\n\n"
                "输出格式（严格JSON）：\n"
                '{"adjustments": [{"line": "...", "param": "...", "old_value": x, "new_value": y, "reason": "..."}]}'
            ),
            user_prompt=f"当前状态:\n{sim_snapshot}\n\n告警:\n{alerts}\n\n目标产线: {target_line}"
        )

        # 解析LLM输出的调整指令
        parsed = self._parse_adjustments(llm_result or "{}")

        # 注入仿真引擎——实际修改产线参数
        applied = self._apply_to_simulator(parsed)

        return {
            "output": self._format_adjustment_report(applied),
            "applied_adjustments": applied,
        }

    def _apply_to_simulator(self, adjustments: list) -> list:
        """将调整指令写入仿真引擎"""
        import streamlit as st
        applied = []
        sim = st.session_state.get("simulation_engine")
        if sim is None:
            return applied

        for adj in adjustments:
            line = adj["line"]
            param = adj["param"]
            new_val = adj["new_value"]
            old_val = adj["old_value"]
            reason = adj.get("reason", "")

            # 调用仿真器接口
            sim.apply_adjustment(line, param, new_val)

            applied.append({
                "line": line,
                "param": param,
                "old_value": old_val,
                "new_value": new_val,
                "reason": reason,
                "timestamp": time.strftime("%H:%M:%S"),
            })

            # 写入调整日志（Tab2可见）
            sim.adjustment_log.append({
                "time": time.strftime("%H:%M:%S"),
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

### 4.5 StrategyWorker 更新

StrategyWorker 的 system prompt 根据场景动态调整。新增半导体场景prompt：

```python
# 当检测到产线场景时，prompt变为：
"你是半导体制造领域的资深工艺整合工程师。请基于上游多个专业Agent的分析结果，"
"生成一份全面的产线综合诊断与决策报告。要求：\n"
"1. 先总结各产线的关键异常和健康状态（2-3句话概述）\n"
"2. 列出3-5条具体的、可操作的工艺调整或维护建议，每条包含行动方案和理由\n"
"3. 评估主要风险和缓解措施（如调整过度导致新问题）\n"
"4. 预测调整后的预期效果（良率回升幅度、恢复时间）\n"
"5. 用具体数据和趋势支撑结论，不要空洞的套话\n"
"6. 输出2000-4000字，确保内容完整不截断"
```

---

## 第五章  对话与记忆系统

### 5.1 ChatLLM 多轮对话原理

ChatLLM 是对话管理器，负责维护多轮对话上下文。系统角色已更新为半导体产线智能助手。

### 5.2 工作流检测机制

`is_workflow_request()` 判断用户输入是普通对话还是触发多Agent工作流。关键词列表新增：

```python
workflow_keywords = [
    # ... 原有关键词 ...
    "检测", "监控", "产线", "良率", "产能", "OEE", "DPPM",
    "光刻", "刻蚀", "测试", "调整", "补偿", "漂移", "故障",
]
```

### 5.3 会话状态管理

新增仿真相关的session state变量：

```python
DEFAULTS = {
    # ... 原有变量 ...
    "simulation_engine": None,      # SemiconductorSimulator 实例
    "simulation_active": False,     # 仿真是否运行中
    "simulation_data": {},          # 当前帧数据
    "simulation_history": [],       # 历史数据（最近60帧）
    "simulation_log": [],           # 事件和调整日志
    "auto_check_enabled": True,     # 自动检测调整开关
    "auto_check_interval": 300,     # 自动检测间隔（秒）
    "tab": "对话",                  # 当前激活Tab
}
```

---

## 第六章  产线仿真引擎

### 6.1 仿真模型总览

系统内置半导体产线仿真器，独立线程运行，每秒产出一帧数据。仿真三条产线：光刻(Lithography) → 刻蚀(Etching) → 测试(Testing)。

### 6.2 每条产线的数据模型

统一数据结构，每秒刷新：

```python
{
    "timestamp": "2026-06-14 14:35:22",
    "production_lines": {
        "litho": {
            "name": "光刻线 #L1",
            "output": 118,           # 当前小时产出(片)
            "yield_rate": 0.963,     # 良率(0-1)
            "oee": 0.84,             # 设备综合效率(0-1)
            "status": "running",     # running / warning / alarm / idle
            "params": {
                "exposure_dose": 25.3,     # 曝光剂量 mJ/cm²
                "focus_offset": 12.5,      # 焦距偏移 nm
                "alignment_error": 0.8     # 对位误差 nm
            }
        },
        "etch": {
            "name": "刻蚀线 #E1",
            "output": 92,
            "yield_rate": 0.938,
            "oee": 0.81,
            "status": "warning",
            "params": {
                "rf_power": 510,           # RF功率 W
                "chamber_pressure": 32.1,  # 腔室压力 mTorr
                "etch_rate": 98.3          # 刻蚀速率 nm/min
            }
        },
        "test": {
            "name": "测试线 #T1",
            "throughput": 198,       # 检测吞吐 units/h
            "dppm": 462,             # 缺陷率 DPPM
            "utilization": 0.77,     # 设备利用率
            "status": "running",
            "bin_distribution": {    # Bin分类统计
                "bin1_good": 0.87,
                "bin2_repairable": 0.08,
                "bin3_scrap": 0.05
            }
        }
    },
    "events": []  # 当前触发的异常事件
}
```

### 6.3 仿真核心算法

```python
class SemiconductorSimulator:
    """半导体产线仿真引擎 — 独立线程运行"""

    def __init__(self):
        self.lines = {
            "litho": LineState(base_output=120, base_yield=0.965, drift_rate=0.0002),
            "etch":  LineState(base_output=95,  base_yield=0.940, drift_rate=0.0003),
            "test":  LineState(base_output=200, base_yield=0.0,   drift_rate=0.0),
        }
        self.elapsed_seconds = 0
        self.adjustment_log = []  # Agent调整记录
        self.event_log = []       # 异常事件记录
        self._running = False

    def tick(self) -> dict:
        """每秒调用一次，返回当前帧数据"""
        self.elapsed_seconds += 1

        for name, line in self.lines.items():
            # 1. 基础波动：正负5%随机噪声
            line.current_output = line.base_output * (0.95 + random() * 0.1)
            line.current_yield = line.base_yield * (0.98 + random() * 0.04)
            line.current_oee = 0.78 + random() * 0.10

        # 2. 工艺漂移：良率随时间缓慢下降（模拟光刻胶老化）
        drift = self.elapsed_seconds / 3600 * 0.0007
        self.lines["litho"].current_yield -= drift
        self.lines["etch"].current_yield -= drift * 1.2

        # 3. 上游影响下游
        self.lines["test"].dppm = int(
            300 + (1 - self.lines["litho"].current_yield) * 3000 +
            (1 - self.lines["etch"].current_yield) * 2500
        )
        self.lines["test"].bin3 = (
            0.03 + (1 - self.lines["litho"].current_yield) * 0.3 +
            (1 - self.lines["etch"].current_yield) * 0.25
        )

        # 4. 随机异常事件注入
        event = self._maybe_trigger_event()

        return self._build_frame(event)

    def apply_adjustment(self, line: str, param: str, value: float):
        """子Agent调用此方法调整产线参数"""
        if line in self.lines:
            old = getattr(self.lines[line], param, None)
            if old is not None:
                setattr(self.lines[line], param, value)
                # 调整效果：设置恢复趋势（良率将在2分钟内回升约1-2%）
                self.lines[line]._recovery_trend = +0.015
```

### 6.4 四种异常事件

模拟半导体产线真实痛点：

| 事件 | 触发概率 | 现象 | Agent可做调整 |
|------|---------|------|-------------|
| **光刻胶老化** | 每30分钟 | 光刻良率5分钟内降3-5% | 曝光剂量+2 mJ/cm²补偿 |
| **刻蚀速率漂移** | 每45分钟 | 刻蚀速率偏离±8% | RF功率±50W调整 |
| **设备OEE突降** | 每60分钟 | OEE降至60%以下 | 建议PM排程 |
| **测试线堆积** | 每40分钟 | 利用率>95%且DPPM上升 | 调整采样频率 |

### 6.5 仿真器与Streamlit集成

仿真器通过 st.session_state 共享数据：

```python
# app.py 中启动仿真线程
def start_simulation():
    if not st.session_state.simulation_engine:
        st.session_state.simulation_engine = SemiconductorSimulator()

    def _run_loop():
        while st.session_state.simulation_active:
            frame = st.session_state.simulation_engine.tick()
            st.session_state.simulation_data = frame
            # 保留最近60帧用于趋势图
            st.session_state.simulation_history.append(frame)
            if len(st.session_state.simulation_history) > 60:
                st.session_state.simulation_history.pop(0)
            time.sleep(1)

    thread = threading.Thread(target=_run_loop, daemon=True)
    thread.start()
```

---

## 第七章  产线监控仪表盘

### 7.1 Tab2 整体布局

```
┌──────────────────────────────────────────────────────────────┐
│ 🏭 产线监控仪表盘                                            │
│ ┌─────────────────────────┐  ┌─────────────────────────────┐ │
│ │ 🔁 自动检测调整 [ON ✓]   │  │ 仿真引擎 [▶ 运行中]         │ │
│ │ 间隔 [5]分钟  [3][5][10] │  │ 运行时长: 02:34:12          │ │
│ └─────────────────────────┘  └─────────────────────────────┘ │
├──────────┬──────────┬──────────┬────────────────────────────┤
│ 光刻线L1 │ 刻蚀线E1 │ 测试线T1 │  📋 调整日志               │
│ ⚠️ 警告  │ ✅ 运行  │ ⚠️ 堆积  │                             │
│ 产出 118 │ 产出  92 │ 吞吐 198 │  14:32 [自动] 调整光刻线   │
│ 良率 96% │ 良率 93% │ DPPM 462│  曝光剂量 +1.5 (25→26.5)   │
│ OEE  84% │ OEE  81% │ 利用率77%│  14:35 [手动] 调整刻蚀线   │
│          │          │ Bin分布  │  RF功率 -30W (540→510)     │
│          │          │ 良87/修8│  14:40 [自动] 全部正常 ✅   │
│          │          │ 废5%    │                             │
├──────────┴──────────┴──────────┴────────────────────────────┤
│ 📈 良率趋势 (近60分钟)                                       │
│  1.00 ┤                                                    │
│  0.95 ┤━━━━━━━━━━━━━━━━━╮  ← 调整标记 ── 回升              │
│  0.90 ┤                 ╰──────────────                    │
│       ├────┬────┬────┬────┬────┬────                       │
│       14:00 14:10 14:20 14:30 14:40 14:50                  │
│       ▓▓ 光刻  ▓▓ 刻蚀  ▓▓ 测试                             │
│                                                             │
│ 📈 产出台账 (每小时产出)                                     │
│ ▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊ 118 (光刻)                                │
│ ▊▊▊▊▊▊▊▊▊▊▊▊   92 (刻蚀)                                 │
│ ▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊▊ 198 (测试)                         │
│                                                             │
│ ⚡ 事件时间线                                                │
│ 14:28 [告警] 光刻线良率异常下降 (96.5%→93.2%)               │
│ 14:30 [自动调整] 曝光剂量补偿 +1.5 (25.0→26.5)              │
│ 14:32 [恢复] 光刻线良率回升至95.8%                          │
│ 14:45 [告警] 测试线DPPM超标 (623)                           │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 核心图表实现

使用 Streamlit 原生 chart + metric 组件：

- **产线指标卡片**：`st.metric` 三列布局，颜色根据status动态变化
- **良率趋势图**：`st.line_chart` 展示三条产线近60分钟良率变化
- **产出台账**：`st.bar_chart` 展示每小时产能对比
- **事件时间线**：`st.expander` + 自定义HTML渲染日志流

### 7.3 调整标记可视化

当Agent执行调整时，图表上出现竖虚线标记，hover显示调整内容。使用 `st.altair_chart` 实现：

```python
import altair as alt

def render_yield_chart(history, adjustments):
    # 良率曲线
    yield_data = []
    for frame in history:
        for line_id, data in frame["production_lines"].items():
            yield_data.append({
                "time": frame["timestamp"],
                "line": data["name"],
                "yield_rate": data["yield_rate"],
            })

    base = alt.Chart(yield_data).mark_line().encode(
        x="time:T", y="yield_rate:Q", color="line:N"
    )

    # 调整标记竖线
    rules = alt.Chart(adjustments).mark_rule(
        color="red", strokeDash=[4, 4]
    ).encode(
        x="time:T",
        tooltip=["time", "param", "old_value", "new_value"]
    )

    return base + rules
```

---

## 第八章  对话-监控联动与双模式设计

### 8.1 联动架构

```
                    st.session_state (共享数据总线)
                 ┌───────────────────────────────────┐
                 │  simulation_data                   │
                 │  simulation_history                │
                 │  simulation_active                 │
                 │  simulation_log (事件/调整)         │
                 │  auto_check_enabled                │
                 └───────┬─────────────┬─────────────┘
                         │             │
          ┌──────────────┴──┐    ┌─────┴──────────────┐
          │   Tab1: 对话     │    │  Tab2: 监控仪表盘    │
          │                 │    │                     │
          │ 手动工作流触发   │    │ 实时图表渲染         │
          │ Monitor Worker  │←───│ 产线指标更新         │
          │ Adjuster Worker─┼───→│ 调整标记+日志        │
          │ 诊断报告卡片     │    │ 自动检测循环         │
          │ 系统消息推送     │←───│ 异常事件通知         │
          └─────────────────┘    └─────────────────────┘
```

### 8.2 四个联动触点

**触点1：聊天触发"产线检测"**
用户说"检查三条产线的状态" → Monitor Worker从simulation_data读取 → 趋势分析 → 诊断报告卡片出现在聊天中。

**触点2：聊天触发"产线调整"**
用户说"调整光刻线曝光剂量" → Adjuster Worker计算并写入仿真器 → 聊天出现调整确认卡片 + Tab2图表出现红色调整标记线 + 良率曲线开始回升。

**触点3：自动异常主动推送**
仿真器触发异常事件 → 自动循环检测到 → 轻量规则调整 → 在Tab1聊天中插入系统消息：
```
[14:28] 🤖 ⚠️ 光刻线 #L1 良率异常下降
       当前: 93.2% (基线: 96.5%) | 已自动补偿曝光剂量 +1.5
```
用户可点击"深入分析"触发完整手动工作流。

**触点4：调整日志双向可见**
Tab2右侧调整日志流展示全部调整记录，区分 `[自动]` 和 `[手动]` 标签。

### 8.3 双模式设计

#### 自动模式（轻量级循环）

- **触发**：Tab2界面开关 `🔁 自动检测调整 [ON/OFF]` + 间隔下拉
- **执行内容**：阈值检测（良率掉3% / OEE<60% / DPPM>600）→ 简单规则补偿
- **不经过**完整LangGraph调度，直接执行单步调整
- **记录**显示在Tab2调整日志，带 `[自动]` 标签
- **总结消息**推送到Tab1聊天

#### 手动模式（深度分析）

- **触发**：用户在Tab1输入产线相关任务
- **执行内容**：完整LangGraph调度 → 多Worker并行 → 深度根因分析 → LLM策略报告
- **记录**显示在Tab1聊天卡片（完整诊断报告）+ Tab2图表调整标记 + `[手动]` 标签日志

#### 协同规则

| 场景 | 行为 |
|------|------|
| 自动刚调整完，用户说"检查产线" | 手动照常执行，报告引用自动调整效果 |
| 手动执行中，自动周期到了 | 跳过本轮，日志"等待手动分析完成" |
| 用户说"关闭自动调整" | 仅停止自动循环，手动仍可用 |
| 用户说"间隔改成3分钟" | 更新循环参数，立即生效 |
| 用户手动调整了参数 | Tab2图表标记+Tooltip，自动感知参数已变 |

### 8.4 典型用户操作场景

| 时间 | 用户操作 | 系统行为 |
|------|---------|---------|
| 14:00 | 打开Tab2，启动仿真 | 三条产线开始运行，数据每秒刷新 |
| 14:10 | 看到光刻线变黄⚠️ | 自动循环已触发，曝光补偿+1.5 |
| 14:12 | 切到Tab1，看到14:10系统消息 | 自动调整的总结消息已推送 |
| 14:13 | 输入"光刻线问题严重吗，帮我深入分析" | 手动模式启动，多Agent全流程 |
| 14:14 | 看到完整诊断报告卡片 | Monitor+Data+ML+Strategy执行完成 |
| 14:15 | 输入"按建议再+2曝光剂量撑住" | Adjuster执行，Tab2图表出现标记 |
| 14:20 | 切回Tab2确认良率回升 | 良率曲线显示回升趋势 |
| 14:30 | 输入"生成今天下午的分析报告" | 导出完整Word/Excel/PDF报告 |

---

## 第九章  技术栈与部署

### 9.1 技术栈

| 层次 | 技术 | 用途 |
|------|------|------|
| 前端 | Streamlit 1.30+ | 多Tab UI、聊天界面、监控仪表盘 |
| 前端图表 | Streamlit原生 + Altair | 折线图、柱状图、指标卡片 |
| 调度 | LangGraph 0.2+ | DAG构建、并行/串行自动调度 |
| LLM接入 | LangChain + OpenAI SDK | structured output意图解析、Worker LLM调用 |
| LLM后端 | DeepSeek API | 对话、意图解析、策略生成 |
| 仿真 | Python threading | 独立线程产线数据生成 |
| 文件导出 | python-docx, openpyxl, fpdf2 | Word/Excel/PDF报告生成 |
| 数据 | pandas | 时序数据处理、图表数据准备 |
| 联网 | DuckDuckGo Search, requests | 外部数据检索、HTTP调用 |

### 9.2 新依赖

```
altair>=5.0          # 高级图表（调整标记等）
# 已有依赖继续使用
streamlit>=1.30.0
langgraph>=0.2.0
langchain-openai>=0.1.0
openai>=1.0.0
pandas>=2.0.0
python-docx>=1.0.0
openpyxl>=3.1.0
fpdf2>=2.7.0
requests>=2.31.0
python-dotenv>=1.0.0
```

### 9.3 部署运行

```bash
# 安装依赖
pip install -r requirements.txt

# 配置API Key（可选，不配置则离线模式）
cp .env.example .env
# 编辑 .env: DEEPSEEK_API_KEY=sk-xxx

# 启动
streamlit run app.py
```

LLM模式：对话使用DeepSeek + Worker输出使用LLM + 仿真数据使用数学模型
离线模式：对话规则匹配 + Worker模拟数据 + 仿真和调度功能完全正常

---

## 第十章  关键代码设计

### 10.1 app.py 重构要点

多Tab架构：

```python
# Tab切换
tab1, tab2 = st.tabs(["💬 智能对话", "📊 产线监控"])

with tab1:
    # 保留现有聊天+工作流逻辑
    # 移除房产/高考等旧示例按钮
    # 新增产线场景示例按钮
    render_chat_tab()

with tab2:
    # 新增产线监控仪表盘
    render_monitoring_dashboard()
```

### 10.2 Tab2渲染函数

```python
def render_monitoring_dashboard():
    """渲染产线监控仪表盘"""

    # === 控制栏 ===
    col_ctrl1, col_ctrl2 = st.columns([0.5, 0.5])
    with col_ctrl1:
        auto_enabled = st.toggle("🔁 自动检测调整", value=st.session_state.auto_check_enabled)
        interval = st.selectbox("间隔", [3, 5, 10], index=1, label_visibility="collapsed")
    with col_ctrl2:
        if st.button("▶ 启动仿真" if not st.session_state.simulation_active else "⏸ 停止仿真"):
            toggle_simulation()

    # === 三条产线指标卡片 ===
    col_l, col_e, col_t, col_log = st.columns([0.22, 0.22, 0.22, 0.34])
    with col_l:
        render_line_card("litho", st.session_state.simulation_data)
    with col_e:
        render_line_card("etch", st.session_state.simulation_data)
    with col_t:
        render_line_card("test", st.session_state.simulation_data)
    with col_log:
        render_adjustment_log(st.session_state.simulation_engine)

    # === 趋势图表 ===
    st.subheader("📈 良率趋势")
    render_yield_chart(st.session_state.simulation_history)

    st.subheader("📊 产出台账")
    render_output_chart(st.session_state.simulation_history)

    # === 事件时间线 ===
    st.subheader("⚡ 事件时间线")
    render_event_timeline(st.session_state.simulation_engine)
```

### 10.3 意图解析补充关键词

```python
TASK_TYPES["production_monitor"] = {
    "keywords": ["检测", "监控", "产线", "良率", "产能", "OEE", "状态",
                 "光刻", "刻蚀", "测试", "异常", "DPPM"],
    "worker": "production_monitor",
    "label": "产线监控",
    "description_template": "读取产线实时数据与历史趋势",
}

TASK_TYPES["production_adjuster"] = {
    "keywords": ["调整", "补偿", "修改参数", "优化工艺", "调参",
                 "曝光剂量", "RF功率", "腔室压力"],
    "worker": "production_adjuster",
    "label": "产线调整",
    "description_template": "计算并执行产线工艺参数调整",
}
```

### 10.4 侧边栏示例更新

```python
examples = [
    ("🔍 产线检测", "全面检测三条产线的运行状态，分析良率和产能异常"),
    ("🔧 自动调整", "光刻线良率持续下降，分析原因并自动调整工艺参数"),
    ("📊 综合分析", "对刻蚀线和测试线进行联合分析，找出良率瓶颈"),
    ("⚡ 故障诊断", "设备OEE突然下降，排查是待料问题还是设备故障"),
    ("📝 生成报告", "生成本周产线运行综合报告，包含趋势和建议"),
]
```

---

## 附录：实现任务清单

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 1 | 创建仿真引擎 | `simulation/` (新) | 半导体产线仿真核心 |
| 2 | 创建产线监控Worker | `workers/production_monitor.py` (新) | 读取仿真数据+初步诊断 |
| 3 | 创建产线调整Worker | `workers/production_adjuster.py` (新) | 计算调整+写入仿真器 |
| 4 | 重构app.py | `app.py` (改) | 多Tab布局+仿真生命周期 |
| 5 | 构建Tab2仪表盘 | `app.py` (改) | 指标卡片+趋势图+日志流 |
| 6 | 更新意图解析 | `meta_agent/intent_parser.py` (改) | 移除旧模板+新增产线模板 |
| 7 | 更新调度引擎 | `meta_agent/langgraph_engine.py` (改) | 注册新Worker类型 |
| 8 | 更新对话角色 | `config.py` (改) | 更新system_prompt+仿真参数 |
| 9 | 双模式自动循环 | `app.py` (改) | 自动检测调整后台循环 |
| 10 | 联动推送机制 | `app.py` (改) | 异常自动推送+调整双向可见 |
| 11 | 更新依赖 | `requirements.txt` (改) | 添加altair等 |

---

*文档版本: v2.0 | 最后更新: 2026-06-14*
*由 Meta-Agent 多智能体协同调度系统设计团队编写*
