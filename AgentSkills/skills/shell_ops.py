"""
Shell 命令执行工具模块

提供在本地 Shell 中执行命令的功能。
"""

import subprocess


def run_shell_command(command: str) -> str:
    """执行 Shell 命令并返回输出

    Args:
        command: 要执行的 Shell 命令字符串

    Returns:
        命令的标准输出和标准错误合并结果，超时或出错时返回错误信息
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Error executing command: {e}"
