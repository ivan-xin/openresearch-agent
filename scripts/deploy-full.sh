#!/bin/bash

# AI Agent 部署脚本
# 用于部署 openresearch-agent 服务

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
AI_AGENT_DIR="$PROJECT_ROOT/ai-agent"
MCP_SERVER_DIR="$PROJECT_ROOT/../openresearch-mcp-server"

# 配置变量
SERVICE_NAME="ai-agent"
SERVICE_USER="ai-agent"
SERVICE_PORT="${PORT:-8000}"
SERVICE_HOST="${HOST:-0.0.0.0}"
ENVIRONMENT="${ENVIRONMENT:-production}"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"

# 显示部署信息
show_deploy_info() {
    log_info "=== AI Agent 部署信息 ==="
    log_info "项目根目录: $PROJECT_ROOT"
    log_info "AI Agent目录: $AI_AGENT_DIR"
    log_info "MCP服务器目录: $MCP_SERVER_DIR"
    log_info "服务名称: $SERVICE_NAME"
    log_info "服务端口: $SERVICE_PORT"
    log_info "服务主机: $SERVICE_HOST"
    log_info "部署环境: $ENVIRONMENT"
    log_info "Python版本: $PYTHON_VERSION"
    log_info "=========================="
}

# 检查系统依赖
check_system_dependencies() {
    log_info "检查系统依赖..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    
    # 检查pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 未安装"
        exit 1
    fi
    
    # 检查systemd (用于服务管理)
    if ! command -v systemctl &> /dev/null; then
        log_warning "systemctl 不可用，将跳过服务安装"
    fi
    
    log_success "系统依赖检查完成"
}

# 检查项目结构
check_project_structure() {
    log_info "检查项目结构..."
    
    # 检查AI Agent目录
    if [ ! -d "$AI_AGENT_DIR" ]; then
        log_error "AI Agent目录不存在: $AI_AGENT_DIR"
        exit 1
    fi
    
    # 检查主文件
    if [ ! -f "$AI_AGENT_DIR/main.py" ]; then
        log_error "主文件不存在: $AI_AGENT_DIR/main.py"
        exit 1
    fi
    
    # 检查配置文件
    if [ ! -f "$AI_AGENT_DIR/configs/settings.py" ]; then
        log_error "配置文件不存在: $AI_AGENT_DIR/configs/settings.py"
        exit 1
    fi
    
    # 检查环境变量文件（在项目根目录）
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_warning "环境变量文件不存在: $PROJECT_ROOT/.env"
    fi
    
    # 检查MCP服务器目录
    if [ ! -d "$MCP_SERVER_DIR" ]; then
        log_warning "MCP服务器目录不存在: $MCP_SERVER_DIR"
        log_warning "请确保 openresearch-mcp-server 项目在正确位置"
    fi
    
    log_success "项目结构检查完成"
}

# 创建服务用户
create_service_user() {
    if [ "$ENVIRONMENT" = "production" ]; then
        log_info "创建服务用户..."
        
        if ! id "$SERVICE_USER" &>/dev/null; then
            sudo useradd --system --shell /bin/false --home-dir /nonexistent --no-create-home "$SERVICE_USER"
            log_success "服务用户 $SERVICE_USER 创建成功"
        else
            log_info "服务用户 $SERVICE_USER 已存在"
        fi
    fi
}

# 设置Python虚拟环境
setup_virtual_environment() {
    log_info "设置Python虚拟环境..."
    
    cd "$AI_AGENT_DIR"
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_success "虚拟环境创建成功"
    else
        log_info "虚拟环境已存在"
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装依赖
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        log_success "依赖安装完成"
    else
        log_warning "requirements.txt 不存在，跳过依赖安装"
    fi
    
    deactivate
}

# 设置MCP服务器环境
setup_mcp_server() {
    if [ -d "$MCP_SERVER_DIR" ]; then
        log_info "设置MCP服务器环境..."
        
        cd "$MCP_SERVER_DIR"
        
        # 创建MCP服务器虚拟环境
        if [ ! -d "venv" ]; then
            python3 -m venv venv
            log_success "MCP服务器虚拟环境创建成功"
        else
            log_info "MCP服务器虚拟环境已存在"
        fi
        
        # 激活虚拟环境并安装依赖
        source venv/bin/activate
        pip install --upgrade pip
        
        if [ -f "requirements.txt" ]; then
            pip install -r requirements.txt
            log_success "MCP服务器依赖安装完成"
        fi
        
        deactivate
        cd "$AI_AGENT_DIR"
    else
        log_warning "跳过MCP服务器设置"
    fi
}

# 处理环境变量文件
setup_environment_file() {
    log_info "处理环境变量文件..."
    
    # 检查项目根目录的.env文件
    if [ -f "$PROJECT_ROOT/.env" ]; then
        log_info "发现项目根目录的.env文件"
        
        # 如果是生产环境，复制并修改配置
        if [ "$ENVIRONMENT" = "production" ]; then
            # 创建生产环境配置
            cp "$PROJECT_ROOT/.env" "$PROJECT_ROOT/.env.production"
            
            # 修改生产环境特定配置
            sed -i.bak "s/DEBUG=true/DEBUG=false/g" "$PROJECT_ROOT/.env.production"
            sed -i.bak "s/LOG_LEVEL=DEBUG/LOG_LEVEL=INFO/g" "$PROJECT_ROOT/.env.production"
            sed -i.bak "s/HOST=localhost/HOST=$SERVICE_HOST/g" "$PROJECT_ROOT/.env.production"
            sed -i.bak "s/PORT=8000/PORT=$SERVICE_PORT/g" "$PROJECT_ROOT/.env.production"
            
            # 数据库配置 - 生产环境通常启用数据库
            sed -i.bak "s/DB_SKIP_IN_DEV=true/DB_SKIP_IN_DEV=false/g" "$PROJECT_ROOT/.env.production"
            
            # 清理备份文件
            rm -f "$PROJECT_ROOT/.env.production.bak"
            
            log_success "生产环境配置文件创建完成"
        fi
    else
        log_warning ".env文件不存在，将创建默认配置"
        create_default_env_file
    fi
}

# 创建默认环境变量文件
create_default_env_file() {
    log_info "创建默认环境变量文件..."
    
    cat > "$PROJECT_ROOT/.env" << EOF
# AI Agent 配置
APP_NAME=AI-Agent
APP_VERSION=1.0.0
DEBUG=${DEBUG:-false}
LOG_LEVEL=${LOG_LEVEL:-INFO}

# 服务器配置
HOST=$SERVICE_HOST
PORT=$SERVICE_PORT

# LLM配置 - Together.ai
LLM_PROVIDER=together
TOGETHER_API_KEY=${TOGETHER_API_KEY:-}
TOGETHER_MODEL=Qwen/Qwen2.5-VL-72B-Instruct
TOGETHER_BASE_URL=https://api.together.xyz/v1/chat/completions
LLM_MAX_TOKENS=2000
LLM_TEMPERATURE=0.7
LLM_TIMEOUT=30

# MCP服务器配置
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8001
MCP_SERVER_TIMEOUT=60
MCP_ENABLE_DEBUG_LOG=true
MCP_DEBUG_LOG_FILE=ai-agent/logs/mcp_debug.log

# MCP 配置 - stdio 协议
MCP_COMMAND=../openresearch-mcp-server/venv/bin/python
MCP_ARGS=["../openresearch-mcp-server/src/main.py"]
MCP_CWD=../openresearch-mcp-server
MCP_TIMEOUT=30
MCP_MAX_RETRIES=3
MCP_RETRY_DELAY=1.0

# 数据库配置
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-openrearch}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-123456}
DATABASE_URL=postgresql://\${DB_USER}:\${DB_PASSWORD}@\${DB_HOST}:\${DB_PORT}/\${DB_NAME}

# 数据库控制 - 生产环境默认启用数据库
DB_SKIP_IN_DEV=${DB_SKIP_IN_DEV:-false}

# 缓存配置
CACHE_TYPE=memory
CACHE_TTL=3600
EOF
    log_success "默认.env文件创建完成"
}

# 创建日志目录
setup_logging() {
    log_info "设置日志目录..."
    
    # 创建日志目录
    mkdir -p "$AI_AGENT_DIR/logs"
    
    # 设置日志目录权限
    if [ "$ENVIRONMENT" = "production" ]; then
        sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$AI_AGENT_DIR/logs"
        sudo chmod -R 755 "$AI_AGENT_DIR/logs"
    else
        chmod -R 755 "$AI_AGENT_DIR/logs"
    fi
    
    log_success "日志目录设置完成"
}

# 设置文件权限
setup_permissions() {
    log_info "设置文件权限..."
    
    if [ "$ENVIRONMENT" = "production" ]; then
        # 生产环境权限设置
        sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$AI_AGENT_DIR"
        sudo chown "$SERVICE_USER:$SERVICE_USER" "$PROJECT_ROOT/.env"*
        sudo chmod -R 755 "$AI_AGENT_DIR"
        sudo chmod 644 "$PROJECT_ROOT/.env"*
        sudo chmod +x "$AI_AGENT_DIR/main.py"
    else
        # 开发环境权限设置
        chmod -R 755 "$AI_AGENT_DIR"
        chmod +x "$AI_AGENT_DIR/main.py"
        chmod 644 "$PROJECT_ROOT/.env"*
    fi
    
    log_success "文件权限设置完成"
}

# 创建systemd服务文件
create_systemd_service() {
    if [ "$ENVIRONMENT" = "production" ] && command -v systemctl &> /dev/null; then
        log_info "创建systemd服务..."
        
        # 确定使用的环境文件
        ENV_FILE="$PROJECT_ROOT/.env.production"
        if [ ! -f "$ENV_FILE" ]; then
            ENV_FILE="$PROJECT_ROOT/.env"
        fi
        
        sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << EOF
[Unit]
Description=AI Agent Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$AI_AGENT_DIR
Environment=PATH=$AI_AGENT_DIR/venv/bin
EnvironmentFile=$ENV_FILE
ExecStart=$AI_AGENT_DIR/venv/bin/python $AI_AGENT_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$AI_AGENT_DIR/logs
ReadWritePaths=$PROJECT_ROOT

[Install]
WantedBy=multi-user.target
EOF
        
        # 重新加载systemd
        sudo systemctl daemon-reload
        sudo systemctl enable "$SERVICE_NAME"
        
        log_success "systemd服务创建完成"
    else
        log_info "跳过systemd服务创建"
    fi
}

# 启动服务
start_service() {
    log_info "启动服务..."
    
    if [ "$ENVIRONMENT" = "production" ] && command -v systemctl &> /dev/null; then
        # 生产环境使用systemd
        sudo systemctl start "$SERVICE_NAME"
        sleep 3
        sudo systemctl status "$SERVICE_NAME" --no-pager
        log_success "服务启动完成"
    else
        # 开发环境直接运行
        log_info "开发环境模式，请手动启动服务:"
        log_info "cd $AI_AGENT_DIR"
        log_info "source venv/bin/activate"
        log_info "python main.py"
    fi
}

# 验证部署
verify_deployment() {
    log_info "验证部署..."
    
    # 等待服务启动
    sleep 5
    
    # 检查端口是否监听
    if command -v netstat &> /dev/null; then
        if netstat -tuln | grep ":$SERVICE_PORT " > /dev/null; then
            log_success "服务端口 $SERVICE_PORT 正在监听"
        else
            log_warning "服务端口 $SERVICE_PORT 未监听"
        fi
    fi
    
    # 检查HTTP响应
    if command -v curl &> /dev/null; then
        if curl -s "http://localhost:$SERVICE_PORT/" > /dev/null; then
            log_success "HTTP服务响应正常"
        else
            log_warning "HTTP服务无响应"
        fi
    fi
}

# 显示部署结果
show_deployment_result() {
    log_success "=== 部署完成 ==="
    log_info "服务地址: http://$SERVICE_HOST:$SERVICE_PORT"
    log_info "API文档: http://$SERVICE_HOST:$SERVICE_PORT/docs"
    log_info "健康检查: http://$SERVICE_HOST:$SERVICE_PORT/api/v1/health"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        log_info ""
        log_info "服务管理命令:"
        log_info "  启动服务: sudo systemctl start $SERVICE_NAME"
        log_info "  停止服务: sudo systemctl stop $SERVICE_NAME"
        log_info "  重启服务: sudo systemctl restart $SERVICE_NAME"
        log_info "  查看状态: sudo systemctl status $SERVICE_NAME"
        log_info "  查看日志: sudo journalctl -u $SERVICE_NAME -f"
    fi
    
    log_info ""
    log_info "配置文件:"
    log_info "  环境变量: $PROJECT_ROOT/.env"
    if [ -f "$PROJECT_ROOT/.env.production" ]; then
        log_info "  生产配置: $PROJECT_ROOT/.env.production"
    fi
    
    log_info ""
    log_info "日志文件:"
    log_info "  应用日志: $AI_AGENT_DIR/logs/app.log"
    log_info "  MCP日志: $AI_AGENT_DIR/logs/mcp_debug.log"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        log_info "  系统日志: sudo journalctl -u $SERVICE_NAME"
    fi
    
    log_success "=================="
}

# 数据库设置提示
show_database_info() {
    log_info ""
    log_info "=== 数据库配置说明 ==="
    log_info "当前数据库配置可能需要根据实际环境调整："
    log_info ""
    log_info "环境变量配置："
    log_info "  DB_HOST - 数据库主机地址"
    log_info "  DB_PORT - 数据库端口 (默认: 5432)"
    log_info "  DB_NAME - 数据库名称"
    log_info "  DB_USER - 数据库用户名"
    log_info "  DB_PASSWORD - 数据库密码"
    log_info "  DB_SKIP_IN_DEV - 开发环境是否跳过数据库 (true/false)"
    log_info ""
    log_info "如需修改数据库配置，请编辑："
    if [ "$ENVIRONMENT" = "production" ] && [ -f "$PROJECT_ROOT/.env.production" ]; then
        log_info "  $PROJECT_ROOT/.env.production"
    else
        log_info "  $PROJECT_ROOT/.env"
    fi
    log_info ""
    log_info "数据库初始化："
    log_info "  cd $AI_AGENT_DIR"
    log_info "  python data/init_db.py"
    log_info "=========================="
}

# 主函数
main() {
    log_info "开始部署 AI Agent 服务..."
    
    show_deploy_info
    check_system_dependencies
    check_project_structure
    create_service_user
    setup_virtual_environment
    setup_mcp_server
    setup_environment_file
    setup_logging
    setup_permissions
    create_systemd_service
    start_service
    verify_deployment
    show_deployment_result
    show_database_info
    
    log_success "AI Agent 部署完成！"
}

# 清理函数
cleanup() {
    log_info "执行清理操作..."
    
    if [ "$ENVIRONMENT" = "production" ] && command -v systemctl &> /dev/null; then
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            sudo systemctl stop "$SERVICE_NAME"
            log_info "服务已停止"
        fi
    fi
}

# 帮助信息
show_help() {
    echo "AI Agent 部署脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help          显示帮助信息"
    echo "  -e, --env ENV       设置部署环境 (development|production, 默认: production)"
    echo "  -p, --port PORT     设置服务端口 (默认: 8000)"
    echo "  -H, --host HOST     设置服务主机 (默认: 0.0.0.0)"
    echo "  --cleanup           清理服务"
    echo ""
    echo "环境变量:"
    echo "  ENVIRONMENT         部署环境"
    echo "  PORT               服务端口"
    echo "  HOST               服务主机"
    echo "  DB_HOST            数据库主机"
    echo "  DB_PORT            数据库端口"
    echo "  DB_NAME            数据库名称"
    echo "  DB_USER            数据库用户"
    echo "  DB_PASSWORD        数据库密码"
    echo "  TOGETHER_API_KEY   Together.ai API密钥"
    echo ""
    echo "示例:"
    echo "  $0                                    # 生产环境部署"
    echo "  $0 -e development                    # 开发环境部署"
    echo "  $0 -p 8080 -H 127.0.0.1             # 指定端口和主机"
    echo "  $0 --cleanup                         # 清理服务"
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -p|--port)
            SERVICE_PORT="$2"
            shift 2
            ;;
        -H|--host)
            SERVICE_HOST="$2"
            shift 2
            ;;
        --cleanup)
            cleanup
            exit 0
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 设置错误处理
trap cleanup EXIT

# 执行主函数
main

