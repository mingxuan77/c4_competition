"""意图解析器 - 将自然语言任务解析为结构化任务描述。

支持两种模式：
1. Mock模式（默认）：基于关键词+规则匹配，零依赖可运行
2. LLM模式：调用 DeepSeek API 进行语义理解
"""

import json
import re
from config import LLM_CONFIG

# 任务类型定义 — 扩充到12种
TASK_TYPES = {
    "retrieval": {
        "keywords": ["搜索", "检索", "查找", "获取", "查询", "爬取", "收集", "数据", "信息",
                     "新闻", "论文", "报告"],
        "worker": "retrieval_worker",
        "label": "数据检索",
        "description_template": "检索'{query}'相关数据",
    },
    "data_processing": {
        "keywords": ["清洗", "处理", "整理", "预处理", "提取", "转换", "格式化", "解析",
                     "统计", "汇总", "ETL", "特征工程"],
        "worker": "data_worker",
        "label": "数据处理",
        "description_template": "对数据进行清洗与预处理",
    },
    "ml_prediction": {
        "keywords": ["预测", "趋势", "回归", "分类", "聚类", "机器学习", "深度学习",
                     "神经网络", "模型", "训练", "拟合", "梯度下降", "销量"],
        "worker": "ml_worker",
        "label": "机器学习",
        "description_template": "基于数据进行机器学习预测分析",
    },
    "algorithm": {
        "keywords": ["优化", "规划", "调度", "最短路径", "排序", "匹配", "推荐",
                     "分配", "决策", "算法", "路径规划", "最大化", "最小化"],
        "worker": "algorithm_worker",
        "label": "算法优化",
        "description_template": "运行优化算法生成方案",
    },
    "security": {
        "keywords": ["安全", "漏洞", "攻击", "防护", "扫描", "防火墙", "加密",
                     "渗透", "审计", "合规", "等保", "入侵", "威胁", "风险评估"],
        "worker": "security_worker",
        "label": "安全分析",
        "description_template": "执行安全扫描与风险评估",
    },
    "code_execution": {
        "keywords": ["运行代码", "执行脚本", "编译", "沙箱", "调试", "部署",
                     "测试用例", "自动化脚本", "CI/CD"],
        "worker": "code_worker",
        "label": "代码执行",
        "description_template": "在安全沙箱中执行代码任务",
    },
    "network": {
        "keywords": ["网络", "拓扑", "流量", "带宽", "延迟", "路由", "DNS",
                     "交换机", "负载均衡", "防火墙规则", "QoS", "VLAN", "SDN"],
        "worker": "network_worker",
        "label": "网络监控",
        "description_template": "分析网络拓扑与流量状态",
    },
    "database": {
        "keywords": ["数据库", "SQL", "查询优化", "索引", "迁移", "备份",
                     "数据仓库", "Redis", "MongoDB", "ETL", "物化视图"],
        "worker": "database_worker",
        "label": "数据库",
        "description_template": "执行数据库查询与优化操作",
    },
    "strategy": {
        "keywords": ["策略", "建议", "方案", "规划", "决策", "输出", "报告生成",
                     "推荐", "行动方案", "总结"],
        "worker": "strategy_worker",
        "label": "策略输出",
        "description_template": "综合各模块结果，生成最终策略建议",
    },
    "report_export": {
        "keywords": ["导出", "PDF", "表格", "图表", "下载", "打印", "Markdown", "HTML",
                     "可视化报告", "统计表", "数据报表"],
        "worker": "report_exporter",
        "label": "报告导出",
        "description_template": "将分析结果导出为表格、Markdown、HTML、PDF 等格式",
    },
    "http_request": {
        "keywords": ["API", "HTTP", "请求", "接口", "webhook", "抓取", "调用",
                     "REST", "POST", "GET", "curl", "fetch", "网址", "链接"],
        "worker": "http_worker",
        "label": "HTTP调用",
        "description_template": "发送HTTP请求调用外部API或抓取网页数据",
    },
    "production_monitor": {
        "keywords": ["检测", "监控", "产线", "良率", "产能", "OEE", "状态",
                     "光刻", "刻蚀", "测试", "异常", "DPPM"],
        "worker": "production_monitor",
        "label": "产线监控",
        "description_template": "读取产线实时数据与历史趋势",
    },
    "production_adjuster": {
        "keywords": ["调整", "补偿", "修改参数", "优化工艺", "调参",
                     "曝光剂量", "RF功率", "腔室压力"],
        "worker": "production_adjuster",
        "label": "产线调整",
        "description_template": "计算并执行产线工艺参数调整",
    },
}

# 预设流程模板 — 半导体产线智能监控 + 通用场景
PRESET_PIPELINES = {
    # ─── 半导体产线场景 ───
    "产线状态检测": {
        "intent": "半导体产线状态检测与异常诊断",
        "tasks": [
            {"task_id": "A", "type": "production_monitor",
             "description": "读取光刻/刻蚀/测试三条产线当前运行指标和历史趋势数据"},
            {"task_id": "B", "type": "data_processing",
             "description": "分析异常趋势：良率下降斜率、OEE波动模式、DPPM变化率"},
            {"task_id": "C", "type": "strategy",
             "description": "综合诊断报告：识别异常产线、推断根因、给出处理建议和优先级"},
            {"task_id": "D", "type": "report_export",
             "description": "导出产线检测报告（Word/Excel/PDF格式）"},
        ],
        "dependencies": {"B": ["A"], "C": ["B"], "D": ["C"]},
    },
    "产线自动调整": {
        "intent": "半导体产线工艺参数智能调整",
        "tasks": [
            {"task_id": "A", "type": "production_monitor",
             "description": "拉取目标产线近30分钟历史数据和当前工艺参数"},
            {"task_id": "B", "type": "ml_prediction",
             "description": "预测当前漂移趋势下未来15分钟的良率变化"},
            {"task_id": "C", "type": "production_adjuster",
             "description": "计算最优工艺参数调整量并写入仿真器执行"},
            {"task_id": "D", "type": "strategy",
             "description": "调整效果评估：预期恢复时间、风险评估、后续监控建议"},
            {"task_id": "E", "type": "report_export",
             "description": "导出调整报告（Word/Excel/PDF格式）"},
        ],
        "dependencies": {"B": ["A"], "C": ["B"], "D": ["C"], "E": ["D"]},
    },
    "产线综合分析": {
        "intent": "半导体产线综合运行分析与瓶颈诊断",
        "tasks": [
            {"task_id": "A", "type": "production_monitor",
             "description": "全量采集三条产线运行数据、事件日志和调整历史"},
            {"task_id": "B", "type": "data_processing",
             "description": "数据清洗与相关性分析：良率-参数关联、OEE瓶颈识别"},
            {"task_id": "C", "type": "ml_prediction",
             "description": "基于历史趋势预测未来2小时良率和产能走势"},
            {"task_id": "D", "type": "strategy",
             "description": "综合决策报告：瓶颈排序、维护优先级、产能优化建议"},
            {"task_id": "E", "type": "report_export",
             "description": "导出综合分析报告（Word/Excel/PDF格式）"},
        ],
        "dependencies": {"B": ["A"], "C": ["B"], "D": ["C"], "E": ["D"]},
    },
    "设备故障诊断": {
        "intent": "半导体设备故障诊断与维护建议",
        "tasks": [
            {"task_id": "A", "type": "production_monitor",
             "description": "读取OEE异常产线的详细设备状态和故障日志"},
            {"task_id": "B", "type": "algorithm",
             "description": "故障模式匹配：比对已知故障特征库，识别可能根因"},
            {"task_id": "C", "type": "strategy",
             "description": "输出故障诊断报告：根因排序、修复建议、预计恢复时间"},
            {"task_id": "D", "type": "report_export",
             "description": "导出故障诊断报告（Word/Excel/PDF格式）"},
        ],
        "dependencies": {"B": ["A"], "C": ["B"], "D": ["C"]},
    },
    # ─── 通用场景 ───
    "数据中心安全运维": {
        "intent": "数据中心安全巡检与网络优化",
        "tasks": [
            {"task_id": "A", "type": "network", "description": "全网拓扑发现与流量基线采集"},
            {"task_id": "B", "type": "security", "description": "漏洞扫描与弱口令检测"},
            {"task_id": "C", "type": "data_processing", "description": "聚合安全事件日志与流量异常指标"},
            {"task_id": "D", "type": "algorithm", "description": "基于图论分析攻击路径与瓶颈链路"},
            {"task_id": "E", "type": "strategy", "description": "生成安全加固方案与网络调优建议"},
        ],
        "dependencies": {"C": ["A", "B"], "D": ["C"], "E": ["D"]},
    },
    "数据分析": {
        "intent": "通用数据分析流程",
        "tasks": [
            {"task_id": "A", "type": "retrieval", "description": "从多数据源获取原始数据"},
            {"task_id": "B", "type": "data_processing", "description": "数据清洗、归一化与特征工程"},
            {"task_id": "C", "type": "ml_prediction", "description": "统计分析与机器学习建模"},
            {"task_id": "D", "type": "strategy", "description": "基于分析结果生成业务建议"},
        ],
        "dependencies": {"B": ["A"], "C": ["B"], "D": ["C"]},
    },
    "智能路由": {
        "intent": "网络智能路由优化",
        "tasks": [
            {"task_id": "A", "type": "network", "description": "获取全网拓扑与实时流量矩阵"},
            {"task_id": "B", "type": "data_processing", "description": "分析拥塞模式与链路利用率趋势"},
            {"task_id": "C", "type": "algorithm", "description": "运行多约束最短路径与负载均衡算法"},
            {"task_id": "D", "type": "strategy", "description": "输出路由策略更新方案与预期收益"},
        ],
        "dependencies": {"B": ["A"], "C": ["B"], "D": ["C"]},
    },
    "安全审计": {
        "intent": "信息系统安全审计与合规检查",
        "tasks": [
            {"task_id": "A", "type": "security", "description": "全量资产扫描与漏洞检测"},
            {"task_id": "B", "type": "database", "description": "审计日志采集与异常行为分析"},
            {"task_id": "C", "type": "data_processing", "description": "关联分析：漏洞-资产-威胁情报"},
            {"task_id": "D", "type": "strategy", "description": "生成等保合规评估报告与修复优先级"},
        ],
        "dependencies": {"C": ["A", "B"], "D": ["C"]},
    },
    "数据库迁移": {
        "intent": "数据库架构迁移与性能优化",
        "tasks": [
            {"task_id": "A", "type": "database", "description": "源库结构分析：表、索引、视图、存储过程"},
            {"task_id": "B", "type": "data_processing", "description": "数据质量评估：重复、缺失、不一致检测"},
            {"task_id": "C", "type": "code_execution", "description": "执行迁移脚本：Schema转换 + 数据迁移"},
            {"task_id": "D", "type": "network", "description": "迁移后网络延迟与连接池状态验证"},
            {"task_id": "E", "type": "strategy", "description": "输出迁移总结与查询性能优化建议"},
        ],
        "dependencies": {"B": ["A"], "C": ["B"], "D": ["C"], "E": ["D"]},
    },
}


class IntentParser:
    """意图解析器"""

    def __init__(self):
        self.use_llm = LLM_CONFIG["enabled"]

    def parse(self, user_input: str) -> dict:
        if self.use_llm and LLM_CONFIG["api_key"]:
            return self._parse_with_llm(user_input)
        return self._parse_with_rules(user_input)

    def _parse_with_rules(self, user_input: str) -> dict:
        """基于规则匹配的意图解析（mock 模式）。"""
        # 先尝试匹配预设模板（关键词组合匹配，命中2个即匹配）
        preset_triggers = {
            "产线状态检测": ["检测", "产线", "良率", "异常", "状态", "监控", "指标", "运行"],
            "产线自动调整": ["调整", "补偿", "修改参数", "优化", "曝光", "RF", "功率", "剂量"],
            "产线综合分析": ["综合", "全面分析", "瓶颈", "报告", "光刻", "刻蚀"],
            "设备故障诊断": ["故障", "宕机", "OEE", "停机", "维修", "维护"],
            "数据中心安全运维": ["安全", "网络", "扫描", "漏洞", "拓扑", "运维"],
            "数据分析": ["数据", "建模", "清洗", "分析"],
            "智能路由": ["路由", "网络", "拓扑", "负载均衡", "路径"],
            "安全审计": ["安全审计", "合规", "等保", "审计"],
            "数据库迁移": ["数据库", "迁移", "SQL", "查询优化", "索引"],
        }
        for preset_name, triggers in preset_triggers.items():
            matched = sum(1 for t in triggers if t in user_input)
            if matched >= 2:
                return PRESET_PIPELINES[preset_name]

        # 动态识别
        detected_types = []
        for task_type, info in TASK_TYPES.items():
            score = sum(1 for kw in info["keywords"] if kw in user_input)
            if score > 0:
                detected_types.append((task_type, score))
        detected_types.sort(key=lambda x: x[1], reverse=True)

        if not detected_types:
            return PRESET_PIPELINES["数据分析"]

        tasks = []
        deps = {}
        prev_id = None
        for i, (ttype, _) in enumerate(detected_types[:5]):
            tid = chr(ord("A") + i)
            info = TASK_TYPES[ttype]
            tasks.append({
                "task_id": tid,
                "type": ttype,
                "description": info["description_template"].format(query=user_input[:20]),
            })
            if prev_id:
                deps[tid] = [prev_id]
            prev_id = tid

        # 确保最后有策略输出
        has_strategy = any(t['type'] == 'strategy' for t in tasks)
        if not has_strategy and len(tasks) < 5:
            tid = chr(ord("A") + len(tasks))
            tasks.append({
                "task_id": tid,
                "type": "strategy",
                "description": "综合各模块结果，生成最终策略建议",
            })
            if prev_id:
                deps[tid] = [prev_id]
            prev_id = tid

        # 始终追加报告导出任务
        has_export = any(t['type'] == 'report_export' for t in tasks)
        if not has_export:
            tid = chr(ord("A") + len(tasks))
            tasks.append({
                "task_id": tid,
                "type": "report_export",
                "description": "将分析结果导出为Word/Excel/PDF报告文件",
            })
            if prev_id:
                deps[tid] = [prev_id]

        return {
            "intent": f"基于输入'{user_input[:30]}...'的复合任务",
            "tasks": tasks,
            "dependencies": deps,
        }

    def _parse_with_llm(self, user_input: str) -> dict:
        """调用 DeepSeek API 进行意图解析。"""
        import openai

        client = openai.OpenAI(
            api_key=LLM_CONFIG["api_key"],
            base_url=LLM_CONFIG["base_url"],
        )

        system_prompt = """你是一个多智能体协同调度系统的意图解析器。将用户请求解析为结构化的任务流水线。

可用任务类型及其含义:
- retrieval: 数据检索(搜索/获取/查询数据)
- data_processing: 数据处理(清洗/ETL/特征工程)
- ml_prediction: 机器学习(预测/分类/回归/训练模型)
- algorithm: 算法优化(路径规划/调度/决策)
- security: 安全分析(漏洞扫描/风险评估/合规审计)
- code_execution: 代码执行(沙箱运行脚本/编译部署)
- network: 网络监控(拓扑发现/流量分析/异常检测)
- database: 数据库(查询优化/迁移/索引/ETL)
- strategy: 策略输出(综合建议/最终方案/报告生成)
- http_request: HTTP调用(调用API/抓取网页/webhook)
- report_export: 报告导出(生成Word/Excel/PDF文件)
- production_monitor: 产线监控(读取仿真数据/检测异常/趋势分析)
- production_adjuster: 产线调整(计算调整量/执行工艺参数修改)

输出严格JSON（不要markdown标记）：
{
    "intent": "一句话总结",
    "tasks": [
        {"task_id": "A", "type": "task_type", "description": "任务描述"},
        ...
    ],
    "dependencies": {"B": ["A"], "C": ["B", "A"], ...}
}

规则:
1. task_id 用大写字母 A,B,C...
2. dependencies 中键是后置任务，值是前置任务列表
3. 最后一步必须是 strategy 类型来生成最终策略
4. 任务数量3-6个
5. 可并行的任务用依赖关系体现（无依赖=可并行）
6. 半导体产线相关任务优先使用 production_monitor 和 production_adjuster"""

        response = client.chat.completions.create(
            model=LLM_CONFIG["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请解析以下任务：{user_input}"},
            ],
            temperature=LLM_CONFIG["temperature"],
            max_tokens=LLM_CONFIG.get("max_tokens", 4096),
        )

        content = response.choices[0].message.content.strip()
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        return json.loads(content)
