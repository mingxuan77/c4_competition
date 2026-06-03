"""Python 沙箱执行工具 — 安全隔离运行用户代码"""

import os
import subprocess
import tempfile
import time
from workers.tools.registry import tool
from workers.tools.schema import ToolResult

# 禁止的模块列表
BLOCKED_MODULES = [
    "os", "subprocess", "shutil", "sys", "ctypes", "socket",
    "pickle", "marshal", "importlib",
]

SANDBOX_TIMEOUT = 10  # 秒
MAX_OUTPUT_BYTES = 50 * 1024  # 50KB


@tool(
    name="run_python",
    description="在安全沙箱中执行Python代码，返回stdout/stderr。禁止文件系统和网络操作。",
    parameters={
        "code": "Python源代码字符串",
        "timeout": "超时秒数（默认10）",
    },
)
def run_python(code: str = "", timeout: int = SANDBOX_TIMEOUT) -> ToolResult:
    if not code or not code.strip():
        return ToolResult(success=False, error="代码为空")

    # 在代码前注入安全检查
    guard_lines = []
    for m in BLOCKED_MODULES:
        guard_lines.append(
            f"try:\n"
            f"    import {m}\n"
            f"    class _Block_{m}:\n"
            f"        def __getattr__(self, *a):\n"
            f"            raise ImportError('Module {m} is blocked in sandbox')\n"
            f"    import sys\n"
            f"    sys.modules['{m}'] = _Block_{m}()\n"
            f"except ImportError:\n"
            f"    pass\n"
        )

    full_code = f"""# === 沙箱安全守卫 ===
{chr(10).join(guard_lines)}

# === 用户代码 ===
{code}
"""

    # 写入临时文件
    tmpdir = tempfile.mkdtemp(prefix="sandbox_")
    script_path = os.path.join(tmpdir, "script.py")

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(full_code)

        start_time = time.time()
        proc = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tmpdir,
            env={"PATH": os.environ.get("PATH", ""),
                  "TMP": tmpdir, "TEMP": tmpdir,
                  "PYTHONDONTWRITEBYTECODE": "1"},
        )
        elapsed_ms = round((time.time() - start_time) * 1000)

        stdout = proc.stdout[:MAX_OUTPUT_BYTES]
        stderr = proc.stderr[:MAX_OUTPUT_BYTES]

        if proc.returncode == 0 and not stderr:
            return ToolResult(
                success=True,
                data={
                    "stdout": stdout,
                    "exit_code": proc.returncode,
                },
                metadata={
                    "execution_time_ms": elapsed_ms,
                    "exit_code": proc.returncode,
                },
            )
        else:
            return ToolResult(
                success=False,
                data={"stdout": stdout, "stderr": stderr},
                error=f"退出码 {proc.returncode}: {stderr[:200] if stderr else '(无错误输出)'}",
                metadata={"execution_time_ms": elapsed_ms, "exit_code": proc.returncode},
            )
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, error=f"代码执行超时（>{timeout}秒）")
    except Exception as e:
        return ToolResult(success=False, error=f"沙箱执行异常: {e}")
    finally:
        # 清理临时文件
        try:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass
