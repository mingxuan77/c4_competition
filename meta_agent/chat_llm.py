"""对话 LLM 管理器 - 多轮对话记忆与回复生成"""

import json
import re
from config import LLM_CONFIG, CHAT_CONFIG, get_llm_client


class ChatLLM:
    """管理多轮对话，调用 LLM 生成回复。"""

    def __init__(self):
        self.system_prompt = CHAT_CONFIG["system_prompt"]

    def chat(self, user_message: str, history: list[dict]) -> str:
        """基于历史对话生成回复。"""
        client = get_llm_client()
        if not client:
            return self._mock_reply(user_message)

        messages = [{"role": "system", "content": self.system_prompt}]
        for h in history[-CHAT_CONFIG["max_history"]:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_message})

        try:
            response = client.chat.completions.create(
                model=LLM_CONFIG["model"],
                messages=messages,
                temperature=CHAT_CONFIG["temperature"],
                max_tokens=CHAT_CONFIG["max_tokens"],
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"⚠️ LLM 调用失败: {e}\n\n我当前以离线模式运行。你可以尝试描述你的任务，系统将使用内置规则进行任务拆解与调度。"

    def _mock_reply(self, user_message: str) -> str:
        """离线模式下的智能回复。"""
        keywords_map = {
            "你好": (
                "你好！我是半导体产线智能监控与决策系统的AI助手。\n\n"
                "我可以帮你：\n"
                "- 📡 实时监控三条产线的运行状态\n"
                "- 🔍 分析良率异常、设备OEE告警等\n"
                "- 🔧 计算并执行工艺参数调整\n"
                "- 📊 调度多Agent协同完成深度分析\n"
                "- 📝 生成综合决策报告\n\n"
                "试试输入「全面检测三条产线的运行状态」开始吧！"
            ),
            "功能": (
                "本系统的核心功能：\n\n"
                "**产线仿真引擎** → 模拟光刻/刻蚀/测试三条产线实时运行\n"
                "**智能意图解析** → 将自然语言需求自动拆解为子任务\n"
                "**DAG并行调度** → LangGraph自动识别并行/串行执行\n"
                "**多Agent协同** → 12类专业Agent各司其职\n"
                "**自动检测调整** → 每N分钟自动检测异常并执行轻量级补偿\n"
                "**策略聚合** → 综合各Agent结果生成最终决策报告\n\n"
                "试试输入一个具体任务吧！"
            ),
            "agent": (
                "系统内置12类专业Agent：\n\n"
                "| Agent | 职责 |\n|-------|------|\n"
                "| 📡 产线监控 | 实时读取产线运行数据 |\n"
                "| 🔧 产线调整 | 计算并执行工艺参数调整 |\n"
                "| 🔍 数据检索 | 搜索、获取多源数据 |\n"
                "| 🧹 数据处理 | 清洗、ETL、趋势分析 |\n"
                "| 🤖 机器学习 | 预测、分类、回归建模 |\n"
                "| ⚙️ 算法优化 | 路径规划、故障匹配 |\n"
                "| 🛡️ 安全分析 | 漏洞扫描、风险评估 |\n"
                "| 🌐 网络监控 | 拓扑发现、流量分析 |\n"
                "| 🗄️ 数据库 | 查询优化、迁移管理 |\n"
                "| 💻 代码执行 | 沙箱安全执行脚本 |\n"
                "| 📊 策略输出 | 综合报告与建议生成 |\n"
                "| 📄 报告导出 | Word/Excel/PDF文件 |"
            ),
            "工作流": (
                "系统工作流程：\n\n"
                "1. **意图解析** — 理解你的自然语言输入\n"
                "2. **任务规划** — 将需求拆解为子任务序列\n"
                "3. **DAG构建** — 建立任务依赖关系图\n"
                "4. **并行调度** — LangGraph自动识别并行/串行\n"
                "5. **结果聚合** — 收集各Agent输出\n"
                "6. **策略报告** — 生成综合分析报告\n\n"
                "这一切都是自动完成的，你只需描述你的需求即可。"
            ),
        }

        for kw, reply in keywords_map.items():
            if kw in user_message:
                return reply

        return (
            f"收到你的消息「{user_message[:50]}」。\n\n"
            f"我当前以**离线模式**运行（未配置LLM API），但核心的产线仿真、"
            f"任务拆解与多Agent调度引擎仍然可用。\n\n"
            f"如果你想让我调度多Agent协同完成一个分析任务，请详细描述你的需求，例如：\n"
            f"- 「全面检测三条产线的运行状态」\n"
            f"- 「光刻线良率异常，帮我分析原因」\n"
            f"- 「对数据中心进行安全巡检」\n\n"
            f"💡 *提示：在侧边栏配置 DeepSeek API Key 可启用完整AI对话能力。*"
        )


def is_workflow_request(user_message: str) -> bool:
    """判断用户输入是否应该触发多Agent工作流。"""
    workflow_keywords = [
        "分析", "预测", "优化", "规划", "评估", "调度", "扫描", "审计",
        "迁移", "建模", "训练", "检索", "清洗", "处理", "报告", "方案",
        "投资", "安全", "网络", "数据库", "趋势", "策略", "建议",
        "执行", "部署", "检测", "监控", "对比", "推荐", "生成",
        "产线", "良率", "产能", "OEE", "DPPM", "光刻", "刻蚀", "测试",
        "调整", "补偿", "漂移", "故障", "工艺", "参数", "剂量",
        "analyze", "predict", "optimize", "scan", "audit", "migrate",
    ]
    # 如果消息较长(>20字)且包含工作流关键词，触发工作流
    if len(user_message) >= 10:
        score = sum(1 for kw in workflow_keywords if kw in user_message)
        if score >= 1:
            return True
    return False
