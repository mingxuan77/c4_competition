"""数据检索 Worker — 联网搜索 + LLM 知识库"""

from workers.base_worker import BaseWorker


def _web_search(query: str, max_results: int = 5) -> str:
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(f"- {r['title']}: {r['body'][:200]}")
        return "\n".join(results) if results else ""
    except Exception:
        return ""


class RetrievalWorker(BaseWorker):
    def __init__(self):
        super().__init__("RetrievalWorker")

    def execute(self, task: dict) -> dict:
        result = self._simulate_work(task.get("description", ""))
        desc = task.get("description", "")

        search_results = _web_search(desc, max_results=5)

        prompt = f"检索任务: {desc}"
        if search_results:
            prompt += f"\n\n网络搜索结果:\n{search_results[:2000]}\n\n请基于搜索结果整理关键信息。"
        else:
            prompt += "\n\n请利用你的知识提供相关信息，给出具体数据和名称。"

        llm_output = self._call_llm(
            system_prompt="你是数据检索专家。提供具体信息：真实名称、数值、数据。简洁输出，不要重复，不要占位符。用中文，200-400字。",
            user_prompt=prompt,
        )

        if llm_output:
            result["output"] = llm_output
        else:
            result["output"] = f"[数据检索] 关于「{desc[:40]}」检索完成"
        return result


class DataWorker(BaseWorker):
    def __init__(self):
        super().__init__("DataWorker")

    def execute(self, task: dict) -> dict:
        result = self._simulate_work(task.get("description", ""))
        desc = task.get("description", "")

        llm_output = self._call_llm(
            system_prompt="你是数据处理专家。输出分类汇总、关键指标。简洁，有数值，用中文，100-200字。",
            user_prompt=f"整理以下数据: {desc}",
        )

        if llm_output:
            result["output"] = llm_output
        else:
            result["output"] = f"[数据处理] 数据整理完成"
        return result


class ReportWorker(BaseWorker):
    def __init__(self):
        super().__init__("ReportWorker")

    def execute(self, task: dict) -> dict:
        result = self._simulate_work(task.get("description", ""))
        result["output"] = f"[报告生成] 完成"
        return result
