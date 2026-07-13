"""
Git 操作工具模块

提供全面的 Git 仓库管理功能，包括仓库初始化、克隆、提交、分支管理、
远程同步、配置管理、标签管理以及 .gitignore 文件管理等。
所有操作均通过 subprocess 调用本地 git 命令实现。
"""

import os
import subprocess


def _run_git_command(args: list, cwd: str = None) -> str:
    """执行 Git 命令的内部辅助函数

    Args:
        args: Git 命令参数列表（不含 'git' 前缀）
        cwd: 命令执行的工作目录（仓库根目录）

    Returns:
        命令的标准输出，出错时返回错误信息
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            return f"Git error: {error_msg}"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "Git command timed out"
    except FileNotFoundError:
        return "Git not found. Please install Git first."
    except Exception as e:
        return f"Error executing git command: {e}"


def check_git_installed() -> str:
    """检查 Git 是否已安装并返回版本信息

    Returns:
        Git 版本信息字符串，如 "git version 2.39.3"；未安装时返回错误信息
    """
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return "Git is not installed or not found in PATH."
    except FileNotFoundError:
        return "Git is not installed. Please install Git first."
    except Exception as e:
        return f"Error checking Git installation: {e}"


def git_init(project_path: str) -> str:
    """在指定目录初始化一个新的 Git 仓库

    Args:
        project_path: 项目目录路径（如果目录不存在会自动创建）

    Returns:
        成功或失败的消息
    """
    try:
        # 确保目录存在
        os.makedirs(project_path, exist_ok=True)
        result = _run_git_command(["init"], cwd=project_path)
        if result.startswith("Git error"):
            return result
        return f"✅ 已初始化 Git 仓库: {os.path.abspath(project_path)}"
    except Exception as e:
        return f"Error initializing Git repository: {e}"


def git_clone(repo_url: str, target_dir: str = None) -> str:
    """克隆远程仓库到本地

    Args:
        repo_url: 远程仓库 URL（支持 HTTPS 和 SSH）
        target_dir: 目标目录名（可选，默认使用仓库名）

    Returns:
        成功或失败的消息
    """
    args = ["clone", repo_url]
    if target_dir:
        args.append(target_dir)

    result = _run_git_command(args)
    if result.startswith("Git error"):
        return result
    return f"✅ 已克隆仓库: {repo_url}"


def git_status(project_path: str) -> str:
    """查看当前仓库的工作区状态

    Args:
        project_path: Git 仓库路径

    Returns:
        格式化的状态信息，包括变更的文件列表
    """
    result = _run_git_command(["status"], cwd=project_path)
    if result.startswith("Git error"):
        return result
    return result


def git_add(project_path: str, files: str = ".") -> str:
    """将文件变更添加到暂存区（支持通配符）

    Args:
        project_path: Git 仓库路径
        files: 要暂存的文件路径或通配符模式（默认 "." 表示所有变更）

    Returns:
        成功或失败的消息
    """
    args = ["add", files]
    result = _run_git_command(args, cwd=project_path)
    if result.startswith("Git error"):
        return result
    return f"✅ 已暂存文件: {files}"


def git_commit(project_path: str, message: str, author: str = None) -> str:
    """提交暂存区的变更到仓库

    Args:
        project_path: Git 仓库路径
        message: 提交信息
        author: 作者信息（可选，格式如 "User <user@example.com>"）

    Returns:
        成功或失败的消息，包含提交的哈希值和分支信息
    """
    args = ["commit", "-m", message]
    if author:
        args.extend(["--author", author])

    result = _run_git_command(args, cwd=project_path)
    if result.startswith("Git error"):
        return result
    return f"✅ 提交成功:\n{result}"


def git_log(project_path: str, max_count: int = 10, pretty_format: str = None) -> str:
    """查看提交历史记录

    Args:
        project_path: Git 仓库路径
        max_count: 最大显示条数（默认 10，设为 0 表示不限）
        pretty_format: 自定义输出格式（可选），支持 git log --pretty 格式
                       如 "%h %s (%an, %ad)"，默认使用简洁格式

    Returns:
        格式化的提交历史列表
    """
    args = ["log"]
    if max_count and max_count > 0:
        args.extend([f"--max-count={max_count}"])
    if pretty_format:
        args.extend([f"--pretty=format:{pretty_format}"])
    else:
        args.append("--oneline")

    result = _run_git_command(args, cwd=project_path)
    if result.startswith("Git error"):
        return result
    if not result:
        return "该仓库暂无提交记录。"
    return result


def git_diff(project_path: str, staged: bool = False) -> str:
    """查看工作区与暂存区之间的文件差异

    Args:
        project_path: Git 仓库路径
        staged: 是否查看已暂存（staged）的差异（即 --cached）

    Returns:
        差异内容文本
    """
    args = ["diff"]
    if staged:
        args.append("--cached")

    result = _run_git_command(args, cwd=project_path)
    if result.startswith("Git error"):
        return result
    if not result:
        return "没有发现差异。"
    return result


def git_branch(project_path: str, branch_name: str = None, action: str = "list") -> str:
    """分支管理：查看、创建或删除分支

    Args:
        project_path: Git 仓库路径
        branch_name: 分支名称（创建或删除时需要）
        action: 操作类型，可选值：
                - "list"   ：列出所有分支（默认）
                - "create" ：创建新分支
                - "delete" ：删除分支

    Returns:
        操作结果信息
    """
    if action == "list":
        args = ["branch"]
        result = _run_git_command(args, cwd=project_path)
        if result.startswith("Git error"):
            return result
        # 美化输出
        lines = result.split("\n")
        formatted = ["📦 分支列表:\n"]
        for line in lines:
            if line.startswith("*"):
                formatted.append(f"  🌟 {line}")
            else:
                formatted.append(f"     {line}")
        return "\n".join(formatted) if formatted else "该仓库暂无分支。"

    elif action == "create":
        if not branch_name:
            return "Error: 创建分支时必须提供 branch_name。"
        args = ["branch", branch_name]
        result = _run_git_command(args, cwd=project_path)
        if result.startswith("Git error"):
            return result
        return f"✅ 已创建分支: {branch_name}"

    elif action == "delete":
        if not branch_name:
            return "Error: 删除分支时必须提供 branch_name。"
        args = ["branch", "-d", branch_name]
        result = _run_git_command(args, cwd=project_path)
        if result.startswith("Git error"):
            return result
        return f"✅ 已删除分支: {branch_name}"

    else:
        return f"Error: 未知的操作类型 '{action}'，支持: list, create, delete。"


def git_checkout(project_path: str, branch_name: str, create_new: bool = False) -> str:
    """切换分支

    Args:
        project_path: Git 仓库路径
        branch_name: 要切换到的分支名称
        create_new: 是否创建并切换到新分支（相当于 git checkout -b）

    Returns:
        成功或失败的消息
    """
    args = ["checkout"]
    if create_new:
        args.extend(["-b", branch_name])
    else:
        args.append(branch_name)

    result = _run_git_command(args, cwd=project_path)
    if result.startswith("Git error"):
        return result
    return f"✅ 已切换到分支: {branch_name}"


def git_pull(project_path: str, remote: str = "origin", branch: str = None) -> str:
    """从远程仓库拉取最新变更并合并

    Args:
        project_path: Git 仓库路径
        remote: 远程仓库名称（默认 "origin"）
        branch: 要拉取的分支名（可选，默认拉取当前分支）

    Returns:
        拉取操作的结果信息
    """
    args = ["pull", remote]
    if branch:
        args.append(branch)

    result = _run_git_command(args, cwd=project_path)
    if result.startswith("Git error"):
        return result
    return f"✅ 已从 {remote} 拉取更新:\n{result}"


def git_push(project_path: str, remote: str = "origin", branch: str = None) -> str:
    """将本地提交推送到远程仓库

    Args:
        project_path: Git 仓库路径
        remote: 远程仓库名称（默认 "origin"）
        branch: 要推送的分支名（可选，默认推送当前分支）

    Returns:
        推送操作的结果信息
    """
    args = ["push", remote]
    if branch:
        args.append(branch)
    else:
        # 推送当前分支到远程同名分支
        args.append("HEAD")

    result = _run_git_command(args, cwd=project_path)
    if result.startswith("Git error"):
        return result
    return f"✅ 已推送到 {remote}:\n{result}"


def git_ignore(project_path: str, patterns: list) -> str:
    """创建或更新 .gitignore 文件，添加忽略规则

    Args:
        project_path: Git 仓库路径
        patterns: 要添加到 .gitignore 的匹配模式列表
                  例如 [".DS_Store", "__pycache__/", "*.log", ".env"]

    Returns:
        成功或失败的消息，包含已添加的规则列表
    """
    try:
        gitignore_path = os.path.join(project_path, ".gitignore")

        # 读取现有的 .gitignore 内容
        existing_patterns = set()
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        existing_patterns.add(line)

        # 过滤出尚未添加的规则
        new_patterns = []
        for p in patterns:
            if p not in existing_patterns:
                new_patterns.append(p)

        if not new_patterns:
            return "所有规则已存在于 .gitignore 中，无需更新。"

        # 追加新规则
        with open(gitignore_path, "a", encoding="utf-8") as f:
            if os.path.getsize(gitignore_path) > 0:
                # 如果文件已有内容且不以换行结尾，先加换行
                f.write("\n")
            for pattern in new_patterns:
                f.write(pattern + "\n")

        result_msg = f"✅ 已更新 .gitignore，新增 {len(new_patterns)} 条规则:\n"
        for p in new_patterns:
            result_msg += f"  - {p}\n"
        return result_msg.strip()

    except Exception as e:
        return f"Error updating .gitignore: {e}"


def git_config(project_path: str = None, name: str = None, value: str = None,
               scope: str = "local") -> str:
    """查看或设置 Git 配置

    Args:
        project_path: Git 仓库路径（local 作用域时需要）
        name: 配置项名称（如 "user.name", "user.email"）
              不提供时则列出当前作用域的所有配置
        value: 配置项的值。不提供时则查看指定配置项的当前值
        scope: 配置作用域，可选 "local"、"global"、"system"（默认 "local"）

    Returns:
        配置信息或操作结果
    """
    if scope not in ("local", "global", "system"):
        return f"Error: 无效的作用域 '{scope}'，支持: local, global, system。"

    # 查看特定配置项的值
    if name and value is None:
        args = ["config", f"--{scope}", "--get", name]
        result = _run_git_command(args, cwd=project_path)
        if result.startswith("Git error"):
            return result
        return f"{name} = {result}"

    # 设置配置项
    if name and value is not None:
        args = ["config", f"--{scope}", name, value]
        result = _run_git_command(args, cwd=project_path)
        if result.startswith("Git error"):
            return result
        return f"✅ 已设置 {scope} 配置: {name} = {value}"

    # 列出所有配置
    args = ["config", f"--{scope}", "--list"]
    result = _run_git_command(args, cwd=project_path)
    if result.startswith("Git error"):
        return result
    if not result:
        return f"该作用域 ({scope}) 下暂无配置。"
    return result


def git_reset(project_path: str, mode: str = "mixed", target: str = "HEAD") -> str:
    """撤销变更（重置当前 HEAD 到指定状态）

    Args:
        project_path: Git 仓库路径
        mode: 重置模式，可选：
              - "soft"  ：仅移动 HEAD，保留暂存区和工作区
              - "mixed" ：移动 HEAD 并重置暂存区，保留工作区（默认）
              - "hard"  ：移动 HEAD 并重置暂存区和工作区（⚠️ 谨慎使用）
        target: 要重置到的目标提交（默认 "HEAD"，也可用提交哈希或 HEAD~1 等）

    Returns:
        操作结果信息
    """
    if mode not in ("soft", "mixed", "hard"):
        return f"Error: 无效的重置模式 '{mode}'，支持: soft, mixed, hard。"

    args = ["reset", f"--{mode}", target]
    result = _run_git_command(args, cwd=project_path)
    if result.startswith("Git error"):
        return result

    mode_descriptions = {
        "soft": "仅移动 HEAD（保留暂存区和工作区）",
        "mixed": "移动 HEAD + 重置暂存区（保留工作区）",
        "hard": "⚠️ 移动 HEAD + 重置暂存区和工作区",
    }
    return f"✅ 已执行 git reset --{mode} 到 {target} ({mode_descriptions[mode]}):\n{result}"


def git_tag(project_path: str, tag_name: str = None, message: str = None,
            action: str = "list") -> str:
    """标签管理：查看、创建或删除标签

    Args:
        project_path: Git 仓库路径
        tag_name: 标签名称（创建或删除时需要）
        message: 标签附注信息（创建附注标签时使用）
        action: 操作类型，可选值：
                - "list"   ：列出所有标签（默认）
                - "create" ：创建新标签
                - "delete" ：删除标签

    Returns:
        操作结果信息
    """
    if action == "list":
        args = ["tag", "--list", "--sort=-v:refname"]
        result = _run_git_command(args, cwd=project_path)
        if result.startswith("Git error"):
            return result
        if not result:
            return "该仓库暂无标签。"
        tags = result.split("\n")
        formatted = ["🏷️  标签列表:\n"]
        for i, tag in enumerate(tags, 1):
            formatted.append(f"  {i}. {tag}")
        return "\n".join(formatted)

    elif action == "create":
        if not tag_name:
            return "Error: 创建标签时必须提供 tag_name。"
        if message:
            # 创建附注标签（annotated tag）
            args = ["tag", "-a", tag_name, "-m", message]
        else:
            # 创建轻量标签（lightweight tag）
            args = ["tag", tag_name]
        result = _run_git_command(args, cwd=project_path)
        if result.startswith("Git error"):
            return result
        tag_type = "附注标签" if message else "轻量标签"
        return f"✅ 已创建 {tag_type}: {tag_name}"

    elif action == "delete":
        if not tag_name:
            return "Error: 删除标签时必须提供 tag_name。"
        args = ["tag", "-d", tag_name]
        result = _run_git_command(args, cwd=project_path)
        if result.startswith("Git error"):
            return result
        return f"✅ 已删除标签: {tag_name}"

    else:
        return f"Error: 未知的操作类型 '{action}'，支持: list, create, delete。"
