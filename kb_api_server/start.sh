#!/usr/bin/env bash
#
# 📚 知识库 API 服务器 — 启动脚本 (macOS/Linux)
# ====================================================
# 使用方法:
#   bash start.sh              # 直接启动
#   LLM_API_KEY=xxx bash start.sh  # 启用 AI 问答
#
# 环境变量:
#   KB_DOCS_DIR   知识库目录    (默认: ./docs)
#   LLM_API_KEY   LLM API 密钥  (可选)
#   LLM_BASE_URL  LLM API 地址  (默认: https://api.deepseek.com)
#   LLM_MODEL     LLM 模型名称  (默认: deepseek-v4-flash)
#   PORT          服务端口      (默认: 8000)
# ====================================================

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════╗"
echo "║     📚 知识库 API 服务器 v1.0.0              ║"
echo "║     基于 RAG 的本地知识库问答服务             ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"

# 切换到脚本所在目录
cd "$(dirname "$0")" || exit 1
PROJECT_DIR=$(pwd)
echo -e "${CYAN}📂 工作目录: ${PROJECT_DIR}${NC}"

# 检查 Python
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v $cmd &> /dev/null; then
        PYTHON_CMD=$cmd
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${YELLOW}❌ 未找到 Python，请安装 Python 3.8+${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo -e "${GREEN}✅ Python: ${PYTHON_VERSION}${NC}"

# 检查并安装依赖
echo ""
echo -e "${YELLOW}📦 检查依赖...${NC}"
$PYTHON_CMD -c "import fastapi" 2>/dev/null && \
$PYTHON_CMD -c "import chromadb" 2>/dev/null && \
$PYTHON_CMD -c "import sentence_transformers" 2>/dev/null
DEP_CHECK=$?

if [ "$DEP_CHECK" -ne 0 ]; then
    echo -e "${YELLOW}📦 正在安装依赖 (可能需要几分钟)...${NC}"
    echo -e "${YELLOW}   💡 如果速度慢，可以使用国内镜像:${NC}"
    echo -e "${YELLOW}      pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple${NC}"
    echo ""
    $PYTHON_CMD -m pip install -r requirements.txt -q
    echo -e "${GREEN}✅ 依赖安装完成${NC}"
else
    echo -e "${GREEN}✅ 依赖已就绪${NC}"
fi

# 检查知识库目录
DOCS_DIR="${KB_DOCS_DIR:-./docs}"
if [ ! -d "$DOCS_DIR" ]; then
    echo ""
    echo -e "${YELLOW}📝 知识库目录 '$DOCS_DIR' 不存在，将自动创建并生成示例文档${NC}"
fi

# 显示配置
echo ""
echo -e "${BLUE}📋 启动配置:${NC}"
echo -e "   📂 知识库目录: ${CYAN}${DOCS_DIR}${NC}"
echo -e "   🗄️  向量数据库: ${CYAN}${CHROMA_DB_DIR:-./chroma_db}${NC}"
echo -e "   🌐 监听地址: ${CYAN}${HOST:-0.0.0.0}:${PORT:-8000}${NC}"
echo -e "   API 文档: ${CYAN}http://localhost:${PORT:-8000}/docs${NC}"

if [ -n "$LLM_API_KEY" ]; then
    echo -e "   🤖 AI 问答: ${GREEN}已启用${NC}"
    echo -e "   🏢 LLM 地址: ${CYAN}${LLM_BASE_URL:-https://api.deepseek.com}${NC}"
    echo -e "   🎯 LLM 模型: ${CYAN}${LLM_MODEL:-deepseek-v4-flash}${NC}"
else
    echo -e "   🤖 AI 问答: ${YELLOW}未启用 (纯检索模式)${NC}"
    echo -e "   💡 设置 ${CYAN}LLM_API_KEY${NC} 环境变量可启用 AI 问答"
fi

# 启动服务
echo ""
echo -e "${GREEN}🚀 正在启动服务器...${NC}"
echo -e "${GREEN}  按 Ctrl+C 停止服务${NC}"
echo ""

exec $PYTHON_CMD server.py
