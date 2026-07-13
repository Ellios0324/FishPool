"""
C 语言项目创建与调试工具模块

提供创建标准 C 项目结构、调试编译、添加模块等功能。
"""

import os
import subprocess


def create_c_project(project_name: str, project_type: str = "console") -> str:
    """创建标准 C 语言项目结构

    Args:
        project_name: 项目名称（也是根目录名）
        project_type: 项目类型：'console'(控制台,默认), 'library'(库), 'sdl'(SDL图形)

    Returns:
        成功或失败的消息
    """
    try:
        # 检查参数
        if not project_name or not project_name.replace("_", "").replace("-", "").isalnum():
            return "Error: Invalid project name. Use letters, numbers, underscores or hyphens."

        valid_types = ["console", "library", "sdl"]
        if project_type not in valid_types:
            return f"Error: Invalid project type '{project_type}'. Must be one of: {', '.join(valid_types)}"

        base_path = os.path.abspath(project_name)

        # 创建目录结构
        dirs = [
            os.path.join(base_path, "src"),
            os.path.join(base_path, "include"),
            os.path.join(base_path, "build"),
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)

        # ── 创建 main.c ──
        if project_type == "console":
            main_code = """#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    printf("========================================\\n");
    printf("  %s\\n", project_name);
    printf("========================================\\n");
    printf("Hello, World!\\\\n");
    printf("Project Type: Console\\\\n");
    printf("========================================\\n");
    return 0;
}
""".replace("project_name", project_name)
        elif project_type == "library":
            main_code = """#include <stdio.h>
#include <stdlib.h>
#include "%s.h"

int main(int argc, char *argv[]) {
    printf("Testing library: %s\\\\n");
    printf("Hello from library project!\\\\n");

    /* TODO: Add library function tests here */
    return 0;
}
""".replace("%s", project_name).replace("project_name", project_name)
        else:  # sdl
            main_code = """#include <stdio.h>
#include <stdlib.h>

#ifdef _WIN32
    #include <SDL.h>
#else
    #include <SDL2/SDL.h>
#endif

int main(int argc, char *argv[]) {
    SDL_Window *window = NULL;
    SDL_Surface *screen_surface = NULL;

    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        printf("SDL could not initialize! SDL_Error: %s\\\\n", SDL_GetError());
        return 1;
    }

    window = SDL_CreateWindow(
        "%s",
        SDL_WINDOWPOS_UNDEFINED,
        SDL_WINDOWPOS_UNDEFINED,
        800, 600,
        SDL_WINDOW_SHOWN
    );

    if (window == NULL) {
        printf("Window could not be created! SDL_Error: %s\\\\n", SDL_GetError());
        SDL_Quit();
        return 1;
    }

    screen_surface = SDL_GetWindowSurface(window);
    SDL_FillRect(screen_surface, NULL, SDL_MapRGB(screen_surface->format, 0xFF, 0xFF, 0xFF));
    SDL_UpdateWindowSurface(window);
    SDL_Delay(2000);

    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}
""".replace("%s", project_name)

        with open(os.path.join(base_path, "src", "main.c"), "w", encoding="utf-8") as f:
            f.write(main_code)

        # ── 创建库头文件（library 类型）──
        if project_type == "library":
            header_code = """#ifndef %s_H
#define %s_H

#ifdef __cplusplus
extern "C" {
#endif

/* TODO: Add your library function declarations here */

#ifdef __cplusplus
}
#endif

#endif /* %s_H */
""".replace("%s", project_name.upper())
            with open(os.path.join(base_path, "include", f"{project_name}.h"), "w", encoding="utf-8") as f:
                f.write(header_code)

        # ── 创建 Makefile ──
        if project_type == "console":
            makefile = """CC = gcc
CFLAGS = -Wall -Wextra -std=c11 -Iinclude
LDFLAGS =
SRCDIR = src
BUILDDIR = build
TARGET = $(BUILDDIR)/%(name)s

# Source files
SRCS = $(wildcard $(SRCDIR)/*.c)
OBJS = $(SRCS:$(SRCDIR)/%.c=$(BUILDDIR)/%.o)

# Debug flags
DEBUG_FLAGS = -g -O0 -DDEBUG
RELEASE_FLAGS = -O2 -DNDEBUG

.PHONY: all debug release clean run

all: debug

debug: CFLAGS += $(DEBUG_FLAGS)
debug: $(TARGET)

release: CFLAGS += $(RELEASE_FLAGS)
release: $(TARGET)

$(BUILDDIR)/%.o: $(SRCDIR)/%.c
	@mkdir -p $(BUILDDIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(TARGET): $(OBJS)
	$(CC) $(OBJS) -o $@ $(LDFLAGS)
	@echo "Build complete: $(TARGET)"

run: debug
	./$(TARGET)

clean:
	rm -rf $(BUILDDIR)
	@echo "Cleaned."

# Dependency generation
depend: $(SRCS)
	$(CC) -MM $(CFLAGS) $^ > .depend

-include .depend
""" % {"name": project_name}
        elif project_type == "library":
            makefile = """CC = gcc
CFLAGS = -Wall -Wextra -std=c11 -Iinclude -fPIC
LDFLAGS =
SRCDIR = src
BUILDDIR = build
TARGET = $(BUILDDIR)/lib%(name)s.a
SHARED_TARGET = $(BUILDDIR)/lib%(name)s.so

SRCS = $(wildcard $(SRCDIR)/*.c)
OBJS = $(SRCS:$(SRCDIR)/%.c=$(BUILDDIR)/%.o)

DEBUG_FLAGS = -g -O0 -DDEBUG
RELEASE_FLAGS = -O2 -DNDEBUG

.PHONY: all debug release clean static shared

all: debug

debug: CFLAGS += $(DEBUG_FLAGS)
debug: static

release: CFLAGS += $(RELEASE_FLAGS)
release: static

static: $(TARGET)
shared: CFLAGS += $(RELEASE_FLAGS)
shared: $(SHARED_TARGET)

$(BUILDDIR)/%.o: $(SRCDIR)/%.c
	@mkdir -p $(BUILDDIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(TARGET): $(OBJS)
	ar rcs $@ $^
	@echo "Static library built: $(TARGET)"

$(SHARED_TARGET): $(OBJS)
	$(CC) -shared -o $@ $^
	@echo "Shared library built: $(SHARED_TARGET)"

clean:
	rm -rf $(BUILDDIR)
	@echo "Cleaned."
""" % {"name": project_name}
        else:  # sdl
            makefile = """CC = gcc
CFLAGS = -Wall -Wextra -std=c11 -Iinclude
LDFLAGS =
SRCDIR = src
BUILDDIR = build
TARGET = $(BUILDDIR)/%(name)s

# SDL2 detection
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
    LDFLAGS += $(shell sdl2-config --libs)
    CFLAGS += $(shell sdl2-config --cflags)
endif
ifeq ($(UNAME_S),Darwin)
    LDFLAGS += -framework SDL2
    CFLAGS += -I/usr/local/include/SDL2
endif
ifeq ($(OS),Windows_NT)
    LDFLAGS += -lmingw32 -lSDL2main -lSDL2
endif

SRCS = $(wildcard $(SRCDIR)/*.c)
OBJS = $(SRCS:$(SRCDIR)/%.c=$(BUILDDIR)/%.o)

DEBUG_FLAGS = -g -O0 -DDEBUG
RELEASE_FLAGS = -O2 -DNDEBUG

.PHONY: all debug release clean run

all: debug

debug: CFLAGS += $(DEBUG_FLAGS)
debug: $(TARGET)

release: CFLAGS += $(RELEASE_FLAGS)
release: $(TARGET)

$(BUILDDIR)/%.o: $(SRCDIR)/%.c
	@mkdir -p $(BUILDDIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(TARGET): $(OBJS)
	$(CC) $(OBJS) -o $@ $(LDFLAGS)
	@echo "Build complete: $(TARGET)"

run: debug
	./$(TARGET)

clean:
	rm -rf $(BUILDDIR)
	@echo "Cleaned."
""" % {"name": project_name}

        with open(os.path.join(base_path, "Makefile"), "w", encoding="utf-8") as f:
            f.write(makefile)

        # ── 创建 .gitignore ──
        gitignore = """# Build output
build/
*.o
*.a
*.so
*.exe

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Dependencies
.depend
"""
        with open(os.path.join(base_path, ".gitignore"), "w", encoding="utf-8") as f:
            f.write(gitignore)

        # ── 创建 README.md ──
        readme = f"""# {project_name}

## 项目类型
{project_type}

## 目录结构
```
.
├── src/          # 源代码目录
│   └── main.c    # 主程序入口
├── include/      # 头文件目录
├── build/        # 构建输出目录
├── Makefile      # 构建配置文件
├── .gitignore    # Git 忽略规则
└── README.md     # 项目说明
```

## 构建命令
- `make`          — 调试模式编译
- `make release`  — 发布模式编译
- `make run`      — 编译并运行
- `make clean`    — 清理构建文件
"""
        with open(os.path.join(base_path, "README.md"), "w", encoding="utf-8") as f:
            f.write(readme)

        return f"✅ C 项目 '{project_name}' 创建成功 (类型: {project_type})\n  路径: {base_path}\n  结构: src/main.c, include/, Makefile, .gitignore, README.md"

    except Exception as e:
        return f"Error creating C project: {e}"


def debug_c_project(project_path: str) -> str:
    """调试 C 项目：检查 Makefile、尝试编译、分析错误

    Args:
        project_path: 项目根目录路径

    Returns:
        编译调试结果和修复建议
    """
    results = []

    try:
        base_path = os.path.abspath(project_path)

        if not os.path.exists(base_path):
            return f"Error: Project path does not exist: {base_path}"

        # 检查目录结构
        results.append(f"📁 项目路径: {base_path}")
        results.append("")

        # 检查关键文件
        makefile_path = os.path.join(base_path, "Makefile")
        src_dir = os.path.join(base_path, "src")
        include_dir = os.path.join(base_path, "include")

        files_status = []
        if os.path.exists(makefile_path):
            files_status.append("✅ Makefile 存在")
        else:
            files_status.append("❌ Makefile 不存在")

        if os.path.exists(src_dir):
            c_files = [f for f in os.listdir(src_dir) if f.endswith(".c")]
            files_status.append(f"✅ src/ 目录存在 ({len(c_files)} 个 .c 文件)")
        else:
            files_status.append("❌ src/ 目录不存在")

        if os.path.exists(include_dir):
            h_files = [f for f in os.listdir(include_dir) if f.endswith(".h")]
            files_status.append(f"✅ include/ 目录存在 ({len(h_files)} 个 .h 文件)")
        else:
            files_status.append("⚠️  include/ 目录不存在（可选）")

        results.append("📋 项目结构检查:")
        for s in files_status:
            results.append(f"   {s}")
        results.append("")

        # 检查 gcc 是否可用
        try:
            gcc_check = subprocess.run(
                ["gcc", "--version"],
                capture_output=True, text=True, timeout=5
            )
            if gcc_check.returncode == 0:
                gcc_version = gcc_check.stdout.split("\n")[0]
                results.append(f"✅ 编译器: {gcc_version}")
            else:
                results.append("❌ gcc 未找到或不可用")
                results.append("💡 建议: 安装 GCC (Ubuntu: apt install build-essential, macOS: xcode-select --install)")
                return "\n".join(results)
        except FileNotFoundError:
            results.append("❌ gcc 未安装")
            results.append("💡 建议: 安装 GCC (Ubuntu: apt install build-essential, macOS: xcode-select --install)")
            return "\n".join(results)
        except subprocess.TimeoutExpired:
            results.append("⚠️  gcc 检查超时")

        results.append("")

        # 尝试编译 (make)
        results.append("🔨 尝试编译...")
        try:
            if os.path.exists(makefile_path):
                build_result = subprocess.run(
                    ["make", "-C", base_path],
                    capture_output=True, text=True, timeout=60
                )
            else:
                # 没有 Makefile，直接用 gcc 编译
                c_files = []
                if os.path.exists(src_dir):
                    c_files = [os.path.join(src_dir, f) for f in os.listdir(src_dir) if f.endswith(".c")]

                if not c_files:
                    results.append("❌ 没有找到 .c 源文件")
                    results.append("💡 建议: 在 src/ 目录下创建 .c 文件")
                    return "\n".join(results)

                build_result = subprocess.run(
                    ["gcc", "-Wall", "-Wextra", "-std=c11", "-o", "build_output"] + c_files,
                    capture_output=True, text=True, timeout=60
                )

            if build_result.returncode == 0:
                results.append("✅ 编译成功！")
                if build_result.stdout.strip():
                    results.append(f"   输出: {build_result.stdout.strip()}")
            else:
                results.append("❌ 编译失败")
                results.append("")

                # 分析编译错误
                stderr = build_result.stderr
                if stderr:
                    results.append("📋 编译错误详情:")
                    # 提取关键错误行（最多20行）
                    error_lines = stderr.split("\n")
                    shown = 0
                    for line in error_lines:
                        if line.strip() and shown < 20:
                            results.append(f"   {line}")
                            shown += 1
                    if len(error_lines) > 20:
                        results.append(f"   ... (还有 {len(error_lines) - 20} 行错误)")

                    results.append("")

                    # 给出常见问题的修复建议
                    suggestions = []
                    if "undefined reference" in stderr:
                        suggestions.append("🔧 未定义引用: 检查是否缺少链接库 (-l) 或源文件未编译")
                    if "implicit declaration" in stderr:
                        suggestions.append("🔧 隐式声明: 检查是否缺少 #include 头文件")
                    if "expected" in stderr and "before" in stderr:
                        suggestions.append("🔧 语法错误: 检查分号、括号、花括号是否匹配")
                    if "no such file" in stderr.lower():
                        suggestions.append("🔧 文件未找到: 检查文件路径和 #include 路径是否正确")
                    if "multiple definition" in stderr:
                        suggestions.append("🔧 重复定义: 检查是否有重复的函数定义，使用 static 或头文件保护")
                    if "segmentation fault" in stderr.lower() or "段错误" in stderr:
                        suggestions.append("🔧 段错误: 检查空指针、数组越界、内存泄漏等问题")

                    if suggestions:
                        results.append("💡 修复建议:")
                        for s in suggestions:
                            results.append(f"   {s}")

        except subprocess.TimeoutExpired:
            results.append("⚠️  编译超时（超过60秒）")
        except Exception as e:
            results.append(f"❌ 编译过程出错: {e}")

        return "\n".join(results)

    except Exception as e:
        return f"Error debugging C project: {e}"


def add_c_module(project_path: str, module_name: str) -> str:
    """在 C 项目中添加新的模块（.c 和 .h 文件）

    Args:
        project_path: 项目根目录路径
        module_name: 模块名称（会创建 module_name.c 和 module_name.h）

    Returns:
        成功或失败的消息
    """
    try:
        if not module_name or not module_name.replace("_", "").isalnum():
            return "Error: Invalid module name. Use letters, numbers and underscores."

        base_path = os.path.abspath(project_path)
        src_dir = os.path.join(base_path, "src")
        include_dir = os.path.join(base_path, "include")

        # 确保目录存在
        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(include_dir, exist_ok=True)

        # 检查是否已存在
        c_file = os.path.join(src_dir, f"{module_name}.c")
        h_file = os.path.join(include_dir, f"{module_name}.h")

        if os.path.exists(c_file):
            return f"⚠️  模块 {module_name}.c 已存在，跳过创建"
        if os.path.exists(h_file):
            return f"⚠️  模块 {module_name}.h 已存在，跳过创建"

        # 创建头文件
        guard = f"{module_name.upper()}_H"
        header_content = f"""/**
 * @file {module_name}.h
 * @brief {module_name} module header
 */

#ifndef {guard}
#define {guard}

#ifdef __cplusplus
extern "C" {{
#endif

/* TODO: Add your function declarations here */

/**
 * @brief Initialize the {module_name} module
 * @return 0 on success, -1 on failure
 */
int {module_name}_init(void);

/**
 * @brief Cleanup the {module_name} module
 */
void {module_name}_cleanup(void);

#ifdef __cplusplus
}}
#endif

#endif /* {guard} */
"""
        with open(h_file, "w", encoding="utf-8") as f:
            f.write(header_content)

        # 创建源文件
        source_content = f"""/**
 * @file {module_name}.c
 * @brief {module_name} module implementation
 */

#include "{module_name}.h"
#include <stdio.h>
#include <stdlib.h>

int {module_name}_init(void) {{
    printf("{module_name}: Initializing...\\n");
    /* TODO: Add initialization code here */
    return 0;
}}

void {module_name}_cleanup(void) {{
    printf("{module_name}: Cleaning up...\\n");
    /* TODO: Add cleanup code here */
}}
"""
        with open(c_file, "w", encoding="utf-8") as f:
            f.write(source_content)

        # 更新 Makefile（如果有的话）
        makefile_path = os.path.join(base_path, "Makefile")
        if os.path.exists(makefile_path):
            with open(makefile_path, "r", encoding="utf-8") as f:
                makefile_content = f.read()

            # 检查是否已经引用该模块
            if module_name not in makefile_content:
                # 添加注释标记模块已添加
                note = f"# Module: {module_name} (added by add_c_module)\n"
                makefile_content = makefile_content.replace(
                    "# Source files",
                    f"# Source files\n# Module: {module_name} (auto-detected by wildcard)"
                )
                # Makefile 使用 wildcard 自动检测 src/*.c，所以不需要手动添加
                with open(makefile_path, "w", encoding="utf-8") as f:
                    f.write(makefile_content)

        return f"✅ 模块 '{module_name}' 添加成功:\n   📄 {c_file}\n   📄 {h_file}"

    except Exception as e:
        return f"Error adding C module: {e}"
