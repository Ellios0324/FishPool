"""
C++ 语言项目创建与调试工具模块

提供创建标准 C++ 项目结构、调试编译、添加模块等功能。
"""

import os
import subprocess


def create_cpp_project(project_name: str, project_type: str = "console") -> str:
    """创建标准 C++ 语言项目结构

    Args:
        project_name: 项目名称（也是根目录名）
        project_type: 项目类型：'console'(控制台,默认), 'library'(库), 'sdl'(SDL图形), 'qt'(Qt框架)

    Returns:
        成功或失败的消息
    """
    try:
        # 检查参数
        if not project_name or not project_name.replace("_", "").replace("-", "").isalnum():
            return "Error: Invalid project name. Use letters, numbers, underscores or hyphens."

        valid_types = ["console", "library", "sdl", "qt"]
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

        # ── 创建 main.cpp ──
        if project_type == "console":
            main_code = f"""#include <iostream>
#include <string>

int main(int argc, char *argv[]) {{
    std::cout << "========================================" << std::endl;
    std::cout << "  {project_name}" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << "Hello, World!" << std::endl;
    std::cout << "Project Type: Console" << std::endl;
    std::cout << "C++ Standard: C++17" << std::endl;
    std::cout << "========================================" << std::endl;
    return 0;
}}
"""
        elif project_type == "library":
            main_code = f"""#include <iostream>
#include "{project_name}.hpp"

int main(int argc, char *argv[]) {{
    std::cout << "Testing library: {project_name}" << std::endl;
    std::cout << "Hello from C++ library project!" << std::endl;

    // TODO: Add library function tests here
    return 0;
}}
"""
        elif project_type == "sdl":
            main_code = """#include <iostream>

#ifdef _WIN32
    #include <SDL.h>
#else
    #include <SDL2/SDL.h>
#endif

int main(int argc, char *argv[]) {
    SDL_Window* window = nullptr;
    SDL_Surface* screen_surface = nullptr;

    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        std::cerr << "SDL could not initialize! SDL_Error: "
                  << SDL_GetError() << std::endl;
        return 1;
    }

    window = SDL_CreateWindow(
        "%s",
        SDL_WINDOWPOS_UNDEFINED,
        SDL_WINDOWPOS_UNDEFINED,
        800, 600,
        SDL_WINDOW_SHOWN
    );

    if (window == nullptr) {
        std::cerr << "Window could not be created! SDL_Error: "
                  << SDL_GetError() << std::endl;
        SDL_Quit();
        return 1;
    }

    screen_surface = SDL_GetWindowSurface(window);
    SDL_FillRect(screen_surface, nullptr,
                 SDL_MapRGB(screen_surface->format, 0xFF, 0xFF, 0xFF));
    SDL_UpdateWindowSurface(window);
    SDL_Delay(2000);

    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}
""" % project_name
        else:  # qt
            main_code = f"""#include <QApplication>
#include <QLabel>
#include <QVBoxLayout>
#include <QWidget>

int main(int argc, char *argv[]) {{
    QApplication app(argc, argv);

    QWidget window;
    window.setWindowTitle("{project_name}");
    window.setMinimumSize(400, 300);

    QVBoxLayout *layout = new QVBoxLayout(&window);

    QLabel *titleLabel = new QLabel("<h1>{project_name}</h1>");
    titleLabel->setAlignment(Qt::AlignCenter);
    layout->addWidget(titleLabel);

    QLabel *msgLabel = new QLabel("Hello, World! This is a Qt application.");
    msgLabel->setAlignment(Qt::AlignCenter);
    layout->addWidget(msgLabel);

    window.show();
    return app.exec();
}}
"""

        with open(os.path.join(base_path, "src", "main.cpp"), "w", encoding="utf-8") as f:
            f.write(main_code)

        # ── 创建库头文件（library 类型）──
        if project_type == "library":
            header_code = f"""#ifndef {project_name.upper()}_HPP
#define {project_name.upper()}_HPP

#include <string>
#include <vector>

namespace {project_name} {{

/**
 * @brief Initialize the library
 * @return true on success, false on failure
 */
bool init();

/**
 * @brief Get the library version string
 * @return Version string
 */
std::string version();

/**
 * @brief Cleanup the library
 */
void cleanup();

}} // namespace {project_name}

#endif /* {project_name.upper()}_HPP */
"""
            with open(os.path.join(base_path, "include", f"{project_name}.hpp"), "w", encoding="utf-8") as f:
                f.write(header_code)

        # ── 创建 Makefile ──
        std_flag = "-std=c++17"

        if project_type == "console":
            makefile = """CXX = g++
CXXFLAGS = -Wall -Wextra %(std)s -Iinclude
LDFLAGS =
SRCDIR = src
BUILDDIR = build
TARGET = $(BUILDDIR)/%(name)s

SRCS = $(wildcard $(SRCDIR)/*.cpp)
OBJS = $(SRCS:$(SRCDIR)/%.cpp=$(BUILDDIR)/%.o)

DEBUG_FLAGS = -g -O0 -DDEBUG
RELEASE_FLAGS = -O2 -DNDEBUG

.PHONY: all debug release clean run

all: debug

debug: CXXFLAGS += $(DEBUG_FLAGS)
debug: $(TARGET)

release: CXXFLAGS += $(RELEASE_FLAGS)
release: $(TARGET)

$(BUILDDIR)/%.o: $(SRCDIR)/%.cpp
	@mkdir -p $(BUILDDIR)
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(TARGET): $(OBJS)
	$(CXX) $(OBJS) -o $@ $(LDFLAGS)
	@echo "Build complete: $(TARGET)"

run: debug
	./$(TARGET)

clean:
	rm -rf $(BUILDDIR)
	@echo "Cleaned."
""" % {"name": project_name, "std": std_flag}
        elif project_type == "library":
            makefile = """CXX = g++
CXXFLAGS = -Wall -Wextra %(std)s -Iinclude -fPIC
LDFLAGS =
SRCDIR = src
BUILDDIR = build
TARGET = $(BUILDDIR)/lib%(name)s.a
SHARED_TARGET = $(BUILDDIR)/lib%(name)s.so

SRCS = $(wildcard $(SRCDIR)/*.cpp)
OBJS = $(SRCS:$(SRCDIR)/%.cpp=$(BUILDDIR)/%.o)

DEBUG_FLAGS = -g -O0 -DDEBUG
RELEASE_FLAGS = -O2 -DNDEBUG

.PHONY: all debug release clean static shared

all: debug

debug: CXXFLAGS += $(DEBUG_FLAGS)
debug: static

release: CXXFLAGS += $(RELEASE_FLAGS)
release: static

static: $(TARGET)
shared: CXXFLAGS += $(RELEASE_FLAGS)
shared: $(SHARED_TARGET)

$(BUILDDIR)/%.o: $(SRCDIR)/%.cpp
	@mkdir -p $(BUILDDIR)
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(TARGET): $(OBJS)
	ar rcs $@ $^
	@echo "Static library built: $(TARGET)"

$(SHARED_TARGET): $(OBJS)
	$(CXX) -shared -o $@ $^
	@echo "Shared library built: $(SHARED_TARGET)"

clean:
	rm -rf $(BUILDDIR)
	@echo "Cleaned."
""" % {"name": project_name, "std": std_flag}
        elif project_type == "sdl":
            makefile = """CXX = g++
CXXFLAGS = -Wall -Wextra %(std)s -Iinclude
LDFLAGS =
SRCDIR = src
BUILDDIR = build
TARGET = $(BUILDDIR)/%(name)s

# SDL2 detection
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
    LDFLAGS += $(shell sdl2-config --libs)
    CXXFLAGS += $(shell sdl2-config --cflags)
endif
ifeq ($(UNAME_S),Darwin)
    LDFLAGS += -framework SDL2
    CXXFLAGS += -I/usr/local/include/SDL2
endif
ifeq ($(OS),Windows_NT)
    LDFLAGS += -lmingw32 -lSDL2main -lSDL2
endif

SRCS = $(wildcard $(SRCDIR)/*.cpp)
OBJS = $(SRCS:$(SRCDIR)/%.cpp=$(BUILDDIR)/%.o)

DEBUG_FLAGS = -g -O0 -DDEBUG
RELEASE_FLAGS = -O2 -DNDEBUG

.PHONY: all debug release clean run

all: debug

debug: CXXFLAGS += $(DEBUG_FLAGS)
debug: $(TARGET)

release: CXXFLAGS += $(RELEASE_FLAGS)
release: $(TARGET)

$(BUILDDIR)/%.o: $(SRCDIR)/%.cpp
	@mkdir -p $(BUILDDIR)
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(TARGET): $(OBJS)
	$(CXX) $(OBJS) -o $@ $(LDFLAGS)
	@echo "Build complete: $(TARGET)"

run: debug
	./$(TARGET)

clean:
	rm -rf $(BUILDDIR)
	@echo "Cleaned."
""" % {"name": project_name, "std": std_flag}
        else:  # qt
            makefile = """CXX = g++
CXXFLAGS = -Wall -Wextra %(std)s -Iinclude -fPIC
LDFLAGS =
SRCDIR = src
BUILDDIR = build
TARGET = $(BUILDDIR)/%(name)s

# Qt detection
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
    CXXFLAGS += $(shell pkg-config --cflags Qt5Core Qt5Widgets 2>/dev/null || echo "-I/usr/include/qt5")
    LDFLAGS += $(shell pkg-config --libs Qt5Core Qt5Widgets 2>/dev/null || echo "-lQt5Core -lQt5Widgets")
endif
ifeq ($(UNAME_S),Darwin)
    CXXFLAGS += -I/usr/local/opt/qt/include
    LDFLAGS += -F/usr/local/opt/qt/lib -framework QtCore -framework QtWidgets
endif
ifeq ($(OS),Windows_NT)
    CXXFLAGS += -I$$(QTDIR)/include
    LDFLAGS += -L$$(QTDIR)/lib -lQt5Core -lQt5Widgets
endif

SRCS = $(wildcard $(SRCDIR)/*.cpp)
OBJS = $(SRCS:$(SRCDIR)/%.cpp=$(BUILDDIR)/%.o)

DEBUG_FLAGS = -g -O0 -DDEBUG
RELEASE_FLAGS = -O2 -DNDEBUG

.PHONY: all debug release clean run

all: debug

debug: CXXFLAGS += $(DEBUG_FLAGS)
debug: $(TARGET)

release: CXXFLAGS += $(RELEASE_FLAGS)
release: $(TARGET)

$(BUILDDIR)/%.o: $(SRCDIR)/%.cpp
	@mkdir -p $(BUILDDIR)
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(TARGET): $(OBJS)
	$(CXX) $(OBJS) -o $@ $(LDFLAGS)
	@echo "Build complete: $(TARGET)"

run: debug
	./$(TARGET)

clean:
	rm -rf $(BUILDDIR)
	@echo "Cleaned."
""" % {"name": project_name, "std": std_flag}

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

# Qt (if applicable)
*.pro.user
moc_*.cpp
ui_*.h
qrc_*.cpp
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
│   └── main.cpp  # 主程序入口
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

## 要求
- C++17 兼容的编译器 (g++ >= 7, clang++ >= 6)
"""
        with open(os.path.join(base_path, "README.md"), "w", encoding="utf-8") as f:
            f.write(readme)

        return f"✅ C++ 项目 '{project_name}' 创建成功 (类型: {project_type})\n  路径: {base_path}\n  结构: src/main.cpp, include/, Makefile, .gitignore, README.md"

    except Exception as e:
        return f"Error creating C++ project: {e}"


def debug_cpp_project(project_path: str) -> str:
    """调试 C++ 项目：检查 Makefile、尝试编译、分析错误

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
            cpp_files = [f for f in os.listdir(src_dir) if f.endswith((".cpp", ".cc", ".cxx"))]
            files_status.append(f"✅ src/ 目录存在 ({len(cpp_files)} 个 .cpp 文件)")
        else:
            files_status.append("❌ src/ 目录不存在")

        if os.path.exists(include_dir):
            hpp_files = [f for f in os.listdir(include_dir) if f.endswith((".hpp", ".h", ".hh"))]
            files_status.append(f"✅ include/ 目录存在 ({len(hpp_files)} 个头文件)")
        else:
            files_status.append("⚠️  include/ 目录不存在（可选）")

        results.append("📋 项目结构检查:")
        for s in files_status:
            results.append(f"   {s}")
        results.append("")

        # 检查 g++ 是否可用
        try:
            gxx_check = subprocess.run(
                ["g++", "--version"],
                capture_output=True, text=True, timeout=5
            )
            if gxx_check.returncode == 0:
                gxx_version = gxx_check.stdout.split("\n")[0]
                results.append(f"✅ 编译器: {gxx_version}")

                # 检测 C++17 支持
                if "c++17" in gxx_check.stdout.lower() or "c++17" in gxx_check.stderr.lower():
                    results.append("✅ C++17 支持: 是")
                else:
                    # 尝试编译一个 C++17 特性
                    test_result = subprocess.run(
                        ["g++", "-std=c++17", "-x", "c++", "-", "-o", "/dev/null"],
                        input="auto x = 1; int main() { return 0; }",
                        capture_output=True, text=True, timeout=10
                    )
                    if test_result.returncode == 0:
                        results.append("✅ C++17 支持: 是")
                    else:
                        results.append("⚠️  C++17 支持: 未知（编译测试失败）")
            else:
                results.append("❌ g++ 未找到或不可用")
                results.append("💡 建议: 安装 g++ (Ubuntu: apt install g++, macOS: xcode-select --install)")
                return "\n".join(results)
        except FileNotFoundError:
            results.append("❌ g++ 未安装")
            results.append("💡 建议: 安装 g++ (Ubuntu: apt install g++, macOS: xcode-select --install)")
            return "\n".join(results)
        except subprocess.TimeoutExpired:
            results.append("⚠️  g++ 检查超时")

        results.append("")

        # 尝试编译
        results.append("🔨 尝试编译...")
        try:
            if os.path.exists(makefile_path):
                build_result = subprocess.run(
                    ["make", "-C", base_path],
                    capture_output=True, text=True, timeout=60
                )
            else:
                # 没有 Makefile，直接用 g++ 编译
                cpp_files = []
                if os.path.exists(src_dir):
                    cpp_files = [os.path.join(src_dir, f) for f in os.listdir(src_dir)
                                 if f.endswith((".cpp", ".cc", ".cxx"))]

                if not cpp_files:
                    results.append("❌ 没有找到 .cpp 源文件")
                    results.append("💡 建议: 在 src/ 目录下创建 .cpp 文件")
                    return "\n".join(results)

                build_result = subprocess.run(
                    ["g++", "-std=c++17", "-Wall", "-Wextra", "-o", "build_output"] + cpp_files,
                    capture_output=True, text=True, timeout=60
                )

            if build_result.returncode == 0:
                results.append("✅ 编译成功！")
                if build_result.stdout.strip():
                    results.append(f"   输出: {build_result.stdout.strip()}")
            else:
                results.append("❌ 编译失败")
                results.append("")

                stderr = build_result.stderr
                if stderr:
                    results.append("📋 编译错误详情:")
                    error_lines = stderr.split("\n")
                    shown = 0
                    for line in error_lines:
                        if line.strip() and shown < 20:
                            results.append(f"   {line}")
                            shown += 1
                    if len(error_lines) > 20:
                        results.append(f"   ... (还有 {len(error_lines) - 20} 行错误)")

                    results.append("")

                    # 给出修复建议
                    suggestions = []
                    if "undefined reference" in stderr:
                        suggestions.append("🔧 未定义引用: 检查是否缺少链接库 (-l) 或模板实现未包含")
                    if "not declared" in stderr:
                        suggestions.append("🔧 未声明: 检查 #include 头文件和 using namespace")
                    if "no match" in stderr and "operator" in stderr:
                        suggestions.append("🔧 运算符匹配失败: 检查运算符重载或类型转换")
                    if "template" in stderr.lower():
                        suggestions.append("🔧 模板错误: 检查模板语法和类型参数")
                    if "expected" in stderr:
                        suggestions.append("🔧 语法错误: 检查分号、括号、花括号、模板尖括号")
                    if "no member" in stderr:
                        suggestions.append("🔧 成员不存在: 检查类名拼写和成员函数声明")
                    if "class" in stderr.lower() and "does not have" in stderr.lower():
                        suggestions.append("🔧 类缺失成员: 检查类定义和继承关系")
                    if "override" in stderr.lower():
                        suggestions.append("🔧 覆盖错误: 检查 virtual 函数签名是否完全匹配")

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
        return f"Error debugging C++ project: {e}"


def add_cpp_module(project_path: str, module_name: str) -> str:
    """在 C++ 项目中添加新的模块（.cpp 和 .hpp 文件）

    Args:
        project_path: 项目根目录路径
        module_name: 模块名称（会创建 module_name.cpp 和 module_name.hpp）

    Returns:
        成功或失败的消息
    """
    try:
        if not module_name or not module_name.replace("_", "").isalnum():
            return "Error: Invalid module name. Use letters, numbers and underscores."

        base_path = os.path.abspath(project_path)
        src_dir = os.path.join(base_path, "src")
        include_dir = os.path.join(base_path, "include")

        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(include_dir, exist_ok=True)

        hpp_file = os.path.join(include_dir, f"{module_name}.hpp")
        cpp_file = os.path.join(src_dir, f"{module_name}.cpp")

        if os.path.exists(hpp_file):
            return f"⚠️  模块 {module_name}.hpp 已存在，跳过创建"
        if os.path.exists(cpp_file):
            return f"⚠️  模块 {module_name}.cpp 已存在，跳过创建"

        # 类名转换：snake_case -> PascalCase
        class_name = "".join(word.capitalize() for word in module_name.split("_"))

        # 创建头文件
        guard = f"{module_name.upper()}_HPP"
        header_content = f"""/**
 * @file {module_name}.hpp
 * @brief {class_name} class declaration
 */

#ifndef {guard}
#define {guard}

#include <string>
#include <iostream>

/**
 * @brief The {class_name} class
 */
class {class_name} {{
public:
    /**
     * @brief Default constructor
     */
    {class_name}();

    /**
     * @brief Destructor
     */
    ~{class_name}();

    /**
     * @brief Copy constructor (deleted)
     */
    {class_name}(const {class_name}&) = delete;

    /**
     * @brief Move constructor (deleted)
     */
    {class_name}({class_name}&&) = delete;

    /**
     * @brief Initialize the module
     * @return true on success
     */
    bool init();

    /**
     * @brief Get module name
     * @return Module name string
     */
    std::string name() const;

    /**
     * @brief Print module info
     */
    void printInfo() const;

private:
    std::string m_name;
    bool m_initialized;
}};

#endif /* {guard} */
"""
        with open(hpp_file, "w", encoding="utf-8") as f:
            f.write(header_content)

        # 创建源文件
        source_content = f"""/**
 * @file {module_name}.cpp
 * @brief {class_name} class implementation
 */

#include "{module_name}.hpp"

{class_name}::{class_name}()
    : m_name("{module_name}")
    , m_initialized(false)
{{
    // Constructor
}}

{class_name}::~{class_name}()
{{
    // Destructor
}}

bool {class_name}::init()
{{
    std::cout << "{module_name}: Initializing..." << std::endl;
    m_initialized = true;
    // TODO: Add initialization code here
    return true;
}}

std::string {class_name}::name() const
{{
    return m_name;
}}

void {class_name}::printInfo() const
{{
    std::cout << "Module: " << m_name << std::endl;
    std::cout << "Status: " << (m_initialized ? "Initialized" : "Not initialized") << std::endl;
}}
"""
        with open(cpp_file, "w", encoding="utf-8") as f:
            f.write(source_content)

        return f"✅ C++ 模块 '{module_name}' 添加成功:\n   📄 {hpp_file}\n   📄 {cpp_file}"

    except Exception as e:
        return f"Error adding C++ module: {e}"
