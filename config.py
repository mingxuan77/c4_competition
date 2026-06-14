"""系统配置模块"""

import os
from dotenv import load_dotenv

load_dotenv()

# LLM 配置 (默认使用 DeepSeek)
LLM_CONFIG = {
    "enabled": os.getenv("LLM_ENABLED", "false").lower() == "true",
    "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
    "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    "model": os.getenv("LLM_MODEL", "deepseek-chat"),
    "temperature": 0.3,
    "max_tokens": 8192,
}

# 对话配置
CHAT_CONFIG = {
    "max_history": 30,
    "temperature": 0.7,
    "max_tokens": 16384,
    "system_prompt": """你是"半导体产线智能监控与决策系统"的智能助手，基于 Internet of Agents 架构。

你的核心能力：
1. **产线状态检测**：实时监控光刻、刻蚀、测试三条产线的运行指标（良率、产能、OEE、DPPM）
2. **异常诊断**：自动识别良率波动、设备OEE告警、工艺参数漂移等异常
3. **智能调整**：计算最优工艺参数（曝光剂量、RF功率、腔室压力等）并自动执行调整
4. **多Agent协同**：管理12类专业Agent，从监控→分析→调整→策略→报告全流程自动化

你可以帮用户：
- 检测产线状态："检查三条产线现在的运行状态"
- 分析异常："光刻线良率持续下降，分析原因"
- 执行调整："把光刻线曝光剂量补偿+2"
- 综合诊断："对全产线做综合分析，找出良率瓶颈"
- 生成报告："生成本周产线运行报告"

当用户描述一个需要多步骤分析的复杂任务时，系统会自动调度多Agent协同工作。
对于简单问答，你会直接以AI助手身份回复。

请用中文回复，保持专业、清晰、有帮助。""",
}

# 调度器配置
SCHEDULER_CONFIG = {
    "max_parallel_tasks": 4,
    "task_timeout_seconds": 30,
}

# Worker 模拟配置
WORKER_CONFIG = {
    "mock_delay_min": 0.3,
    "mock_delay_max": 1.0,
    "mock_failure_rate": 0.0,
}


# 产线仿真配置
SIMULATION_CONFIG = {
    "tick_interval_seconds": 1,     # 仿真帧间隔
    "history_max_frames": 300,      # 最大保留历史帧数（5分钟）
    "auto_check_default_interval": 10,  # 自动检测默认间隔（秒）
    "auto_check_intervals": [10, 20, 30],  # 可选间隔（秒）
    "litho_event_interval_seconds": 20,
    "etch_event_interval_seconds": 30,
    "oee_event_interval_seconds": 40,
    "test_event_interval_seconds": 20,
    "yield_warning_threshold": 0.03,  # 良率警告阈值（下降3%触发）
    "yield_alarm_threshold": 0.05,   # 良率告警阈值（下降5%触发）
    "oee_alarm_threshold": 0.60,     # OEE告警阈值
    "dppm_alarm_threshold": 600,     # DPPM告警阈值
}


def get_llm_client():
    """获取 LLM 客户端实例（如果已配置）。"""
    if not LLM_CONFIG["enabled"] or not LLM_CONFIG["api_key"]:
        return None
    import openai
    return openai.OpenAI(
        api_key=LLM_CONFIG["api_key"],
        base_url=LLM_CONFIG["base_url"],
    )
