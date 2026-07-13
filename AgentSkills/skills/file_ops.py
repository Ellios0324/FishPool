"""
文件操作工具模块

提供文件的读取、写入、删除、目录列表和创建等功能。
"""

import os


def read_file(file_path: str) -> str:
    """读取指定文件的内容

    Args:
        file_path: 文件的路径

    Returns:
        文件内容字符串，如果出错则返回错误信息
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(file_path: str, content: str) -> str:
    """将内容写入指定文件（覆盖写入）

    Args:
        file_path: 文件路径
        content: 要写入的内容

    Returns:
        成功或失败的消息
    """
    try:
        # 自动创建父目录
        parent_dir = os.path.dirname(file_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"


def delete_file(file_path: str) -> str:
    """删除指定文件

    Args:
        file_path: 要删除的文件路径

    Returns:
        成功或失败的消息
    """
    try:
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"
        if os.path.isdir(file_path):
            return f"Path is a directory, use delete_directory instead: {file_path}"
        os.remove(file_path)
        return f"Successfully deleted file: {file_path}"
    except Exception as e:
        return f"Error deleting file: {e}"


def delete_directory(dir_path: str, recursive: bool = False) -> str:
    """删除目录

    Args:
        dir_path: 要删除的目录路径
        recursive: 是否递归删除（如果目录非空，需要设为 True）

    Returns:
        成功或失败的消息
    """
    try:
        if not os.path.exists(dir_path):
            return f"Directory not found: {dir_path}"
        if not os.path.isdir(dir_path):
            return f"Path is not a directory: {dir_path}"
        if recursive:
            import shutil
            shutil.rmtree(dir_path)
            return f"Successfully deleted directory (recursive): {dir_path}"
        else:
            os.rmdir(dir_path)
            return f"Successfully deleted directory: {dir_path}"
    except OSError as e:
        if "Directory not empty" in str(e):
            return f"Error: Directory not empty. Use recursive=True to delete non-empty directories."
        return f"Error deleting directory: {e}"
    except Exception as e:
        return f"Error deleting directory: {e}"


def list_directory(dir_path: str = ".", pattern: str = None) -> str:
    """列出指定目录下的文件和子目录

    Args:
        dir_path: 目录路径（默认当前目录）
        pattern: 可选的文件名过滤模式（如 "*.html", "*.py"），支持 Unix 通配符

    Returns:
        格式化的文件列表字符串
    """
    try:
        if not os.path.exists(dir_path):
            return f"Directory not found: {dir_path}"
        if not os.path.isdir(dir_path):
            return f"Path is not a directory: {dir_path}"

        entries = os.listdir(dir_path)
        if not entries:
            return f"Directory is empty: {dir_path}"

        # 区分文件和目录
        files = []
        directories = []
        for entry in sorted(entries):
            full_path = os.path.join(dir_path, entry)
            if os.path.isdir(full_path):
                directories.append(entry)
            else:
                files.append(entry)

        # 应用过滤模式
        if pattern:
            import fnmatch
            files = [f for f in files if fnmatch.fnmatch(f, pattern)]
            directories = [d for d in directories if fnmatch.fnmatch(d, pattern)]

        output_lines = [f"📁 目录: {os.path.abspath(dir_path)}\n"]

        # 显示子目录
        if directories:
            output_lines.append(f"  子目录 ({len(directories)}):")
            for d in directories:
                output_lines.append(f"    📁 {d}/")
            output_lines.append("")

        # 显示文件
        if files:
            output_lines.append(f"  文件 ({len(files)}):")
            for f in files:
                full_path = os.path.join(dir_path, f)
                size = os.path.getsize(full_path)
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                output_lines.append(f"    📄 {f}  ({size_str})")
            output_lines.append("")

        if not files and not directories:
            return f"目录 {dir_path} 中没有匹配 '{pattern}' 的文件。"

        return "\n".join(output_lines)

    except Exception as e:
        return f"Error listing directory: {e}"


def create_directory(dir_path: str) -> str:
    """创建目录（可递归创建）

    Args:
        dir_path: 要创建的目录路径

    Returns:
        成功或失败的消息
    """
    try:
        if os.path.exists(dir_path):
            return f"Directory already exists: {dir_path}"
        os.makedirs(dir_path, exist_ok=True)
        return f"Successfully created directory: {dir_path}"
    except Exception as e:
        return f"Error creating directory: {e}"
