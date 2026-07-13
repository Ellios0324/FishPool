"""
C# 语言项目创建与调试工具模块

提供创建标准 C# 项目结构、调试编译、添加模块等功能。
"""

import os
import subprocess


def _check_dotnet() -> tuple:
    """检查 dotnet CLI 是否可用

    Returns:
        (available: bool, version: str or None)
    """
    try:
        result = subprocess.run(
            ["dotnet", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, None


def create_csharp_project(project_name: str, project_type: str = "console") -> str:
    """创建标准 C# 项目结构

    优先使用 dotnet CLI 创建项目，如果不可用则手动创建 .csproj 和源代码。

    Args:
        project_name: 项目名称（也是根目录名）
        project_type: 项目类型：'console'(控制台,默认), 'library'(类库),
                      'winforms'(Windows窗体), 'webapi'(Web API)

    Returns:
        成功或失败的消息
    """
    try:
        if not project_name or not project_name.replace("_", "").replace("-", "").isalnum():
            return "Error: Invalid project name. Use letters, numbers, underscores or hyphens."

        valid_types = ["console", "library", "winforms", "webapi"]
        if project_type not in valid_types:
            return f"Error: Invalid project type '{project_type}'. Must be one of: {', '.join(valid_types)}"

        base_path = os.path.abspath(project_name)

        # 检查 dotnet CLI
        dotnet_available, dotnet_version = _check_dotnet()

        if dotnet_available:
            # 使用 dotnet CLI 创建项目
            os.makedirs(base_path, exist_ok=True)

            # 模板名称映射
            template_map = {
                "console": "console",
                "library": "classlib",
                "winforms": "winforms",
                "webapi": "webapi",
            }
            template = template_map[project_type]

            result = subprocess.run(
                ["dotnet", "new", template, "-n", project_name, "-o", base_path, "--force"],
                capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                return f"Error: dotnet CLI failed: {result.stderr.strip() or result.stdout.strip()}"

            # 创建 README.md
            readme = f"""# {project_name}

## 项目类型
{project_type} (.NET)

## 构建命令
- `dotnet build`       — 编译项目
- `dotnet run`         — 运行项目
- `dotnet test`        — 运行测试（如存在）
- `dotnet publish`     — 发布项目
- `dotnet clean`       — 清理构建

## 要求
- .NET SDK >= 6.0
"""
            with open(os.path.join(base_path, "README.md"), "w", encoding="utf-8") as f:
                f.write(readme)

            return f"✅ C# 项目 '{project_name}' 创建成功 (类型: {project_type}, dotnet CLI)\n" \
                   f"  路径: {base_path}\n" \
                   f"  .NET SDK: {dotnet_version}"

        else:
            # dotnet CLI 不可用，手动创建项目结构
            os.makedirs(base_path, exist_ok=True)
            os.makedirs(os.path.join(base_path, "Properties"), exist_ok=True)

            # ── 创建 .csproj 文件 ──
            if project_type == "console":
                csproj = f"""<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <RootNamespace>{project_name}</RootNamespace>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <AssemblyName>{project_name}</AssemblyName>
  </PropertyGroup>

</Project>
"""
                program_cs = f"""namespace {project_name};

/// <summary>
/// Main program class
/// </summary>
class Program
{{
    /// <summary>
    /// Application entry point
    /// </summary>
    /// <param name="args">Command-line arguments</param>
    static void Main(string[] args)
    {{
        Console.WriteLine("========================================");
        Console.WriteLine("  {project_name}");
        Console.WriteLine("========================================");
        Console.WriteLine("Hello, World!");
        Console.WriteLine("Project Type: Console");
        Console.WriteLine("C# Version: 12.0 (.NET 8.0)");
        Console.WriteLine("========================================");
    }}
}}
"""
            elif project_type == "library":
                csproj = f"""<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <RootNamespace>{project_name}</RootNamespace>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <AssemblyName>{project_name}</AssemblyName>
    <GeneratePackageOnBuild>true</GeneratePackageOnBuild>
  </PropertyGroup>

</Project>
"""
                program_cs = f"""namespace {project_name};

/// <summary>
/// Main calculator service class
/// </summary>
public class {project_name}Service
{{
    /// <summary>
    /// Get the service version
    /// </summary>
    public string Version => "1.0.0";

    /// <summary>
    /// Initialize the service
    /// </summary>
    /// <returns>True if initialization succeeded</returns>
    public bool Initialize()
    {{
        Console.WriteLine("{project_name} Service initialized.");
        return true;
    }}

    /// <summary>
    /// Process data
    /// </summary>
    /// <param name="input">Input data</param>
    /// <returns>Processed result</returns>
    public string Process(string input)
    {{
        return $"Processed: {{input}}";
    }}
}}
"""
            elif project_type == "winforms":
                csproj = f"""<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <OutputType>WinExe</OutputType>
    <TargetFramework>net8.0-windows</TargetFramework>
    <RootNamespace>{project_name}</RootNamespace>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <UseWindowsForms>true</UseWindowsForms>
    <AssemblyName>{project_name}</AssemblyName>
  </PropertyGroup>

</Project>
"""
                program_cs = f"""namespace {project_name};

static class Program
{{
    /// <summary>
    /// The main entry point for the application.
    /// </summary>
    [STAThread]
    static void Main()
    {{
        ApplicationConfiguration.Initialize();
        Application.Run(new MainForm());
    }}
}}

/// <summary>
/// Main application form
/// </summary>
public class MainForm : Form
{{
    private Label _titleLabel;
    private Button _clickButton;
    private Label _messageLabel;

    /// <summary>
    /// Initialize the form components
    /// </summary>
    public MainForm()
    {{
        Text = "{project_name}";
        Size = new Size(400, 300);
        StartPosition = FormStartPosition.CenterScreen;

        _titleLabel = new Label
        {{
            Text = "{project_name}",
            Font = new Font("Arial", 18, FontStyle.Bold),
            TextAlign = ContentAlignment.MiddleCenter,
            Dock = DockStyle.Top,
            Height = 50
        }};

        _messageLabel = new Label
        {{
            Text = "Hello, World!",
            TextAlign = ContentAlignment.MiddleCenter,
            Dock = DockStyle.Fill
        }};

        _clickButton = new Button
        {{
            Text = "Click Me!",
            Dock = DockStyle.Bottom,
            Height = 40
        }};
        _clickButton.Click += (s, e) => {{
            _messageLabel.Text = $"Button clicked at: {{DateTime.Now:HH:mm:ss}}";
        }};

        Controls.Add(_titleLabel);
        Controls.Add(_messageLabel);
        Controls.Add(_clickButton);
    }}
}}
"""
            else:  # webapi
                csproj = f"""<Project Sdk="Microsoft.NET.Sdk.Web">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <RootNamespace>{project_name}</RootNamespace>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <AssemblyName>{project_name}</AssemblyName>
  </PropertyGroup>

</Project>
"""
                program_cs = f"""var builder = WebApplication.CreateBuilder(args);

// Add services to the container
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();

// Configure the HTTP request pipeline
if (app.Environment.IsDevelopment())
{{
    app.UseSwagger();
    app.UseSwaggerUI();
}}

app.UseHttpsRedirection();
app.UseAuthorization();
app.MapControllers();

Console.WriteLine("{project_name} Web API starting...");
app.Run();
"""
                # 创建 Controllers 目录和示例控制器
                controllers_dir = os.path.join(base_path, "Controllers")
                os.makedirs(controllers_dir, exist_ok=True)

                controller_cs = f"""using Microsoft.AspNetCore.Mvc;

namespace {project_name}.Controllers;

/// <summary>
/// Sample API controller
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class WeatherController : ControllerBase
{{
    private static readonly string[] Summaries = new[]
    {{
        "Freezing", "Bracing", "Chilly", "Cool", "Mild",
        "Warm", "Balmy", "Hot", "Sweltering", "Scorching"
    }};

    /// <summary>
    /// Get weather forecast
    /// </summary>
    /// <returns>Array of weather forecasts</returns>
    [HttpGet(Name = "GetWeatherForecast")]
    public IEnumerable<WeatherForecast> Get()
    {{
        return Enumerable.Range(1, 5).Select(index => new WeatherForecast
        {{
            Date = DateOnly.FromDateTime(DateTime.Now.AddDays(index)),
            TemperatureC = Random.Shared.Next(-20, 55),
            Summary = Summaries[Random.Shared.Next(Summaries.Length)]
        }})
        .ToArray();
    }}
}}

/// <summary>
/// Weather forecast model
/// </summary>
public class WeatherForecast
{{
    /// <summary>Date</summary>
    public DateOnly Date {{ get; set; }}

    /// <summary>Temperature in Celsius</summary>
    public int TemperatureC {{ get; set; }}

    /// <summary>Temperature in Fahrenheit</summary>
    public int TemperatureF => 32 + (int)(TemperatureC / 0.5556);

    /// <summary>Weather summary</summary>
    public string? Summary {{ get; set; }}
}}
"""
                with open(os.path.join(controllers_dir, "WeatherController.cs"), "w", encoding="utf-8") as f:
                    f.write(controller_cs)

            csproj_path = os.path.join(base_path, f"{project_name}.csproj")
            with open(csproj_path, "w", encoding="utf-8") as f:
                f.write(csproj)

            program_path = os.path.join(base_path, "Program.cs")
            with open(program_path, "w", encoding="utf-8") as f:
                f.write(program_cs)

            # ── 创建 README.md ──
            readme = f"""# {project_name}

## 项目类型
{project_type} (.NET, 手动创建)

## 目录结构
```
.
├── Program.cs         # 主程序入口
├── {project_name}.csproj  # 项目文件
├── Properties/        # 项目属性目录
└── README.md          # 项目说明
```

## 构建命令
- `dotnet build`       — 编译项目
- `dotnet run`         — 运行项目
- `dotnet clean`       — 清理构建

## 要求
- .NET SDK >= 6.0
"""
            with open(os.path.join(base_path, "README.md"), "w", encoding="utf-8") as f:
                f.write(readme)

            return f"✅ C# 项目 '{project_name}' 创建成功 (类型: {project_type}, 手动模式)\n" \
                   f"  路径: {base_path}\n" \
                   f"  注意: dotnet CLI 未检测到，已手动创建项目文件"

    except Exception as e:
        return f"Error creating C# project: {e}"


def debug_csharp_project(project_path: str) -> str:
    """调试 C# 项目：检测 dotnet CLI、尝试编译、分析错误

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

        # 检查 dotnet CLI
        dotnet_available, dotnet_version = _check_dotnet()

        if dotnet_available:
            results.append(f"✅ .NET SDK: {dotnet_version}")
        else:
            results.append("❌ dotnet CLI 未找到")
            results.append("💡 建议: 从 https://dotnet.microsoft.com/download 安装 .NET SDK")
            return "\n".join(results)
        results.append("")

        # 检查项目结构
        csproj_files = [f for f in os.listdir(base_path) if f.endswith(".csproj")]
        if csproj_files:
            results.append(f"✅ 项目文件: {csproj_files[0]}")

            # 读取目标框架
            csproj_path = os.path.join(base_path, csproj_files[0])
            with open(csproj_path, "r", encoding="utf-8") as f:
                csproj_content = f.read()

            import re
            tf_match = re.search(r"<TargetFramework>(.*?)</TargetFramework>", csproj_content)
            if tf_match:
                results.append(f"📌 目标框架: {tf_match.group(1)}")
        else:
            results.append("❌ 未找到 .csproj 项目文件")
            results.append("💡 建议: 在项目目录下创建 .csproj 文件")
            return "\n".join(results)

        # 检查源代码
        cs_files = []
        for root, _, files in os.walk(base_path):
            cs_files.extend([os.path.join(root, f) for f in files if f.endswith(".cs")])
        results.append(f"📄 源文件: {len(cs_files)} 个 .cs 文件")

        # 检查 Program.cs
        program_path = os.path.join(base_path, "Program.cs")
        if os.path.exists(program_path):
            results.append("✅ Program.cs 存在")
        else:
            results.append("⚠️  Program.cs 未找到（可能是库项目）")

        results.append("")

        # 尝试编译
        results.append("🔨 尝试编译 (dotnet build)...")
        try:
            build_result = subprocess.run(
                ["dotnet", "build", base_path, "--nologo"],
                capture_output=True, text=True, timeout=120
            )

            if build_result.returncode == 0:
                results.append("✅ 编译成功！")
                # 提取 Build succeeded 相关信息
                output_lines = build_result.stdout.split("\n")
                for line in output_lines:
                    if "->" in line and any(x in line for x in [".dll", ".exe"]):
                        results.append(f"   📦 输出: {line.strip()}")
                        break
            else:
                results.append("❌ 编译失败")
                results.append("")

                stderr = build_result.stderr
                stdout = build_result.stdout

                # 合并输出
                all_output = stderr + "\n" + stdout

                # 提取错误信息
                results.append("📋 编译错误详情:")
                error_lines = []
                for line in all_output.split("\n"):
                    if any(word in line.lower() for word in ["error ", "error cs", "warning cs", "error:", "严重"]) \
                       and line.strip():
                        error_lines.append(line.strip())

                if error_lines:
                    shown = 0
                    for line in error_lines[:20]:
                        results.append(f"   {line}")
                        shown += 1
                    if len(error_lines) > 20:
                        results.append(f"   ... (还有 {len(error_lines) - 20} 条错误/警告)")
                else:
                    # 显示最后几行
                    output_parts = all_output.split("\n")
                    start = max(0, len(output_parts) - 15)
                    for line in output_parts[start:]:
                        if line.strip():
                            results.append(f"   {line.strip()}")

                results.append("")

                # 给出修复建议
                suggestions = []
                if "CS0116" in all_output:
                    suggestions.append("🔧 CS0116: 命名空间不能直接包含成员，请确保代码在 class 内")
                if "CS0103" in all_output:
                    suggestions.append("🔧 CS0103: 名称不存在，检查变量名、using 语句或引用")
                if "CS0117" in all_output:
                    suggestions.append("🔧 CS0117: 类型不包含成员，检查方法/属性名是否正确")
                if "CS0234" in all_output:
                    suggestions.append("🔧 CS0234: 命名空间不存在，检查 using 和 NuGet 包引用")
                if "CS0246" in all_output:
                    suggestions.append("🔧 CS0246: 类型/命名空间未找到，添加 using 或安装 NuGet 包")
                if "CS1001" in all_output:
                    suggestions.append("🔧 CS1001: 标识符未找到，检查拼写错误")
                if "CS1503" in all_output:
                    suggestions.append("🔧 CS1503: 参数类型不匹配，检查方法签名")
                if "CS1729" in all_output:
                    suggestions.append("🔧 CS1729: 类型没有带此参数的构造函数")
                if "NU" in all_output and "error" in all_output.lower():
                    suggestions.append("🔧 NuGet 错误: 运行 'dotnet restore' 恢复 NuGet 包")
                if "NETSDK" in all_output:
                    suggestions.append("🔧 .NET SDK 错误: 检查目标框架是否与已安装的 SDK 版本兼容")

                if suggestions:
                    results.append("💡 修复建议:")
                    for s in suggestions:
                        results.append(f"   {s}")

        except subprocess.TimeoutExpired:
            results.append("⚠️  编译超时（超过120秒）")
        except Exception as e:
            results.append(f"❌ 编译过程出错: {e}")

        return "\n".join(results)

    except Exception as e:
        return f"Error debugging C# project: {e}"


def add_csharp_module(project_path: str, module_name: str) -> str:
    """在 C# 项目中添加新的模块（.cs 文件）

    Args:
        project_path: 项目根目录路径
        module_name: 模块/类名称

    Returns:
        成功或失败的消息
    """
    try:
        if not module_name or not module_name.replace("_", "").isalnum():
            return "Error: Invalid module name. Use letters, numbers and underscores."

        base_path = os.path.abspath(project_path)

        # 自动检测命名空间
        namespace = module_name  # 默认
        csproj_files = [f for f in os.listdir(base_path) if f.endswith(".csproj")]
        if csproj_files:
            csproj_path = os.path.join(base_path, csproj_files[0])
            with open(csproj_path, "r", encoding="utf-8") as f:
                csproj_content = f.read()
            import re
            ns_match = re.search(r"<RootNamespace>(.*?)</RootNamespace>", csproj_content)
            if ns_match:
                namespace = ns_match.group(1)

        # 类名转换：snake_case -> PascalCase
        class_name = "".join(word.capitalize() for word in module_name.split("_"))

        src_file = os.path.join(base_path, f"{class_name}.cs")

        if os.path.exists(src_file):
            return f"⚠️  文件 {class_name}.cs 已存在，跳过创建"

        # 创建 C# 类文件
        content = f"""namespace {namespace};

/// <summary>
/// {class_name} - Module description
/// </summary>
public class {class_name}
{{
    /// <summary>
    /// Initializes a new instance of the <see cref="{class_name}"/> class.
    /// </summary>
    public {class_name}()
    {{
        Name = "{class_name}";
        IsInitialized = false;
    }}

    /// <summary>
    /// Gets the name of this module
    /// </summary>
    public string Name {{ get; private set; }}

    /// <summary>
    /// Gets whether this module is initialized
    /// </summary>
    public bool IsInitialized {{ get; private set; }}

    /// <summary>
    /// Initialize the module
    /// </summary>
    /// <returns>True if successful</returns>
    public bool Initialize()
    {{
        Console.WriteLine($"{{Name}}: Initializing...");
        IsInitialized = true;
        // TODO: Add initialization logic
        return true;
    }}

    /// <summary>
    /// Print module information
    /// </summary>
    public void PrintInfo()
    {{
        Console.WriteLine($"Module: {{Name}}");
        Console.WriteLine($"Status: {{(IsInitialized ? "Initialized" : "Not initialized")}}");
    }}

    /// <summary>
    /// Returns a string representation
    /// </summary>
    public override string ToString()
    {{
        return $"{{Name}} [{{(IsInitialized ? "Ready" : "Not Ready")}}]";
    }}
}}
"""
        with open(src_file, "w", encoding="utf-8") as f:
            f.write(content)

        return f"✅ C# 模块 '{class_name}' 添加成功:\n   📄 {src_file}"

    except Exception as e:
        return f"Error adding C# module: {e}"
