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
    "max_tokens": 4096,
}

# 对话配置
CHAT_CONFIG = {
    "max_history": 30,
    "temperature": 0.7,
    "max_tokens": 8192,
    "system_prompt": """你是"跨域分布式多智能体协同调度系统"的智能助手，基于 Internet of Agents 架构。

你的核心能力：
1. **任务拆解与调度**：将复杂任务自动拆解为子任务DAG，调度多个专业Agent并行执行
2. **多Agent协同**：管理9类专业Agent（数据检索、数据处理、机器学习、算法优化、安全分析、网络监控、数据库、代码执行、策略输出）
3. **全流程自动化**：从意图理解→任务规划→DAG构建→并行调度→结果聚合→策略报告

你可以帮用户：
- 分析复杂业务问题并调度多Agent协同解决
- 回答技术问题，提供专业建议
- 执行数据分析、安全评估、网络优化等工作流
- 生成综合策略报告

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


def get_llm_client():
    """获取 LLM 客户端实例（如果已配置）。"""
    if not LLM_CONFIG["enabled"] or not LLM_CONFIG["api_key"]:
        return None
    import openai
    return openai.OpenAI(
        api_key=LLM_CONFIG["api_key"],
        base_url=LLM_CONFIG["base_url"],
    )
