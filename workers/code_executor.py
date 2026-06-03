"""代码执行 Worker — 接入真实 Python 沙箱执行用户代码"""

from workers.base_worker import BaseWorker


class CodeWorker(BaseWorker):
    """真正的代码执行器——在安全沙箱中运行 Python 代码。"""

    def __init__(self):
        super().__init__("CodeWorker")

    def execute(self, task: dict) -> dict:
        desc = task.get("description", "")
        result = {"worker": self.name}

        # 从 task 中提取代码
        code = task.get("params", {}).get("code", "")
        timeout = task.get("params", {}).get("timeout", 10)

        if not code:
            # 没有代码时，用 LLM 生成代码再执行
            llm_code = self._call_llm(
                system_prompt=(
                    "你是一个Python代码生成器。根据任务描述生成简洁的Python代码。"
                    "只输出代码，不要markdown标记，不要解释。"
                    "用 print() 输出关键结果。"
                ),
                user_prompt=f"任务: {desc}\n\n生成Python代码:",
            )
            if llm_code:
                # 去除可能的 markdown 代码块标记
                code = llm_code.strip()
                if code.startswith("```"):
                    lines = code.split("\n")
                    code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            else:
                result["output"] = "[代码执行] 未提供代码且 LLM 不可用，跳过执行"
                return result

        # 调用沙箱执行
        sandbox_result = self._call_tool("run_python", code=code, timeout=timeout)

        if sandbox_result.get("success"):
            data = sandbox_result.get("data", {})
            stdout = data.get("stdout", "")
            meta = sandbox_result.get("metadata", {})
            result["output"] = (
                f"[代码执行] ✅ 沙箱执行成功\n"
                f"耗时: {meta.get('execution_time_ms', 0)}ms "
                f"| 退出码: {meta.get('exit_code', 0)}\n"
                f"```\n{stdout[:500]}\n```"
            )
        else:
            data = sandbox_result.get("data", {})
            stderr = data.get("stderr", "")
            result["output"] = (
                f"[代码执行] ❌ 执行失败\n"
                f"错误: {sandbox_result.get('error', '未知错误')}\n"
                f"```\n{stderr[:300] if stderr else ''}\n```"
            )

        result["sandbox_result"] = sandbox_result
        return result
