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

# 创建配置文件
create_config_files() {
    log_info "创建配置文件..."
    
    cd "$AI_AGENT_DIR"
    
    # 创建.env文件
    if [ ! -f ".env" ]; then
        cat > .env << EOF
# AI Agent 配置
APP_NAME=AI-Agent
APP_VERSION=1.0.0
DEBUG=${DEBUG:-false}

# 服务器配置
HOST=$SERVICE_HOST
PORT=$SERVICE_PORT

# 日志配置
LOG_LEVEL=${LOG_LEVEL:-INFO}
LOG_FILE=logs/app.log

# MCP服务器配置
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8001
MCP_SERVER_TIMEOUT=60
MCP_ENABLE_DEBUG_LOG=true
MCP_DEBUG_LOG_FILE=logs/mcp_debug.log

# 数据库配置
DATABASE_URL=${DATABASE_URL:-}

# 缓存配置
CACHE_TYPE=memory
CACHE_TTL=3600

# 会话配置
MAX_CONVERSATION_LENGTH=100
EOF
        log_success ".env 文件创建成功"
    else
        log_info ".env 文件已存在"
    fi
    
    # 创建日志目录
    mkdir -p logs
    log_success "日志目录创建完成"
}

# 设置文件权限
setup_permissions() {
    log_info "设置文件权限..."
    
    if [ "$ENVIRONMENT" = "production" ]; then
        # 生产环境权限设置
        sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$AI_AGENT_DIR"
        sudo chmod -R 755 "$AI_AGENT_DIR"
        sudo chmod -R 644 "$AI_AGENT_DIR"/*.py
        sudo chmod +x "$AI_AGENT_DIR/main.py"
        
        # 日志目录权限
        sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$AI_AGENT_DIR/logs"
        sudo chmod -R 755 "$AI_AGENT_DIR/logs"
    else
        # 开发环境权限设置
        chmod -R 755 "$AI_AGENT_DIR"
        chmod +x "$AI_AGENT_DIR/main.py"
    fi
    
    log_success "文件权限设置完成"
}

# 创建systemd服务文件
create_systemd_service() {
    if [ "$ENVIRONMENT" = "production" ] && command -v systemctl &> /dev/null; then
        log_info "创建systemd服务..."
        
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
    log_info "日志文件:"
    log_info "  应用日志: $AI_AGENT_DIR/logs/app.log"
    log_info "  MCP日志: $AI_AGENT_DIR/logs/mcp_debug.log"
    log_success "=================="
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
    create_config_files
    setup_permissions
    create_systemd_service
    start_service
    verify_deployment
    show_deployment_result
    
    log_success "AI Agent 服务部署完成！"
}

# 处理命令行参数
case "${1:-}" in
    --help|-h)
        echo "AI Agent 部署脚本"
        echo ""
        echo "用法: $0 [选项]"
        echo ""
        echo "环境变量:"
        echo "  ENVIRONMENT    部署环境 (development|production, 默认: production)"
        echo "  HOST          服务主机 (默认: 0.0.0.0)"
        echo "  PORT          服务端口 (默认: 8000)"
        echo "  DEBUG         调试模式 (true|false, 默认: false)"
        echo "  LOG_LEVEL     日志级别 (DEBUG|INFO|WARNING|ERROR, 默认: INFO)"
        echo ""
        echo "示例:"
        echo "  $0                                    # 生产环境部署"
        echo "  ENVIRONMENT=development $0            # 开发环境部署"
        echo "  PORT=8080 $0                         # 指定端口部署"
        echo "  DEBUG=true LOG_LEVEL=DEBUG $0        # 调试模式部署"
        exit 0
        ;;
    --check)
        log_info "检查部署环境..."
        show_deploy_info
        check_system_dependencies
        check_project_structure
        log_success "环境检查完成"
        exit 0
        ;;
    --stop)
        log_info "停止服务..."
        if [ "$ENVIRONMENT" = "production" ] && command -v systemctl &> /dev/null; then
            sudo systemctl stop "$SERVICE_NAME"
            log_success "服务已停止"
        else
            log_warning "请手动停止服务进程"
        fi
        exit 0
        ;;
    --restart)
        log_info "重启服务..."
        if [ "$ENVIRONMENT" = "production" ] && command -v systemctl &> /dev/null; then
            sudo systemctl restart "$SERVICE_NAME"
            sudo systemctl status "$SERVICE_NAME" --no-pager
            log_success "服务已重启"
        else
            log_warning "请手动重启服务进程"
        fi
        exit 0
        ;;
    --status)
        log_info "检查服务状态..."
        if [ "$ENVIRONMENT" = "production" ] && command -v systemctl &> /dev/null; then
            sudo systemctl status "$SERVICE_NAME" --no-pager
        else
            # 检查进程
            if pgrep -f "python.*main.py" > /dev/null; then
                log_success "服务进程正在运行"
                ps aux | grep "python.*main.py" | grep -v grep
            else
                log_warning "服务进程未运行"
            fi
        fi
        
        # 检查端口
        if command -v netstat &> /dev/null; then
            if netstat -tuln | grep ":$SERVICE_PORT " > /dev/null; then
                log_success "端口 $SERVICE_PORT 正在监听"
            else
                log_warning "端口 $SERVICE_PORT 未监听"
            fi
        fi
        
        # 检查HTTP响应
        if command -v curl &> /dev/null; then
            log_info "测试HTTP响应..."
            if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$SERVICE_PORT/" | grep -q "200"; then
                log_success "HTTP服务响应正常"
            else
                log_warning "HTTP服务无响应或异常"
            fi
        fi
        exit 0
        ;;
    --logs)
        log_info "查看服务日志..."
        if [ "$ENVIRONMENT" = "production" ] && command -v systemctl &> /dev/null; then
            sudo journalctl -u "$SERVICE_NAME" -f
        else
            if [ -f "$AI_AGENT_DIR/logs/app.log" ]; then
                tail -f "$AI_AGENT_DIR/logs/app.log"
            else
                log_warning "日志文件不存在: $AI_AGENT_DIR/logs/app.log"
            fi
        fi
        exit 0
        ;;
    --uninstall)
        log_warning "卸载服务..."
        read -p "确定要卸载 AI Agent 服务吗? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if [ "$ENVIRONMENT" = "production" ] && command -v systemctl &> /dev/null; then
                sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
                sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || true
                sudo rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
                sudo systemctl daemon-reload
                log_success "systemd服务已卸载"
            fi
            
            # 删除服务用户
            if id "$SERVICE_USER" &>/dev/null; then
                sudo userdel "$SERVICE_USER" 2>/dev/null || true
                log_success "服务用户已删除"
            fi
            
            log_success "服务卸载完成"
        else
            log_info "取消卸载"
        fi
        exit 0
        ;;
    --update)
        log_info "更新服务..."
        
        # 停止服务
        if [ "$ENVIRONMENT" = "production" ] && command -v systemctl &> /dev/null; then
            sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
        fi
        
        # 更新代码 (假设使用git)
        if [ -d "$PROJECT_ROOT/.git" ]; then
            cd "$PROJECT_ROOT"
            git pull origin main || git pull origin master
            log_success "代码更新完成"
        fi
        
        # 更新依赖
        cd "$AI_AGENT_DIR"
        if [ -d "venv" ]; then
            source venv/bin/activate
            pip install --upgrade -r requirements.txt 2>/dev/null || true
            deactivate
            log_success "依赖更新完成"
        fi
        
        # 重启服务
        if [ "$ENVIRONMENT" = "production" ] && command -v systemctl &> /dev/null; then
            sudo systemctl start "$SERVICE_NAME"
            log_success "服务已重启"
        else
            log_info "请手动重启服务"
        fi
        exit 0
        ;;
    --dev)
        log_info "开发模式启动..."
        export ENVIRONMENT=development
        export DEBUG=true
        export LOG_LEVEL=DEBUG
        
        cd "$AI_AGENT_DIR"
        
        # 检查虚拟环境
        if [ ! -d "venv" ]; then
            log_info "创建开发环境..."
            python3 -m venv venv
            source venv/bin/activate
            pip install --upgrade pip
            if [ -f "requirements.txt" ]; then
                pip install -r requirements.txt
            fi
        else
            source venv/bin/activate
        fi
        
        # 创建开发配置
        if [ ! -f ".env.dev" ]; then
            cat > .env.dev << EOF
# 开发环境配置
APP_NAME=AI-Agent-Dev
DEBUG=true
LOG_LEVEL=DEBUG
HOST=127.0.0.1
PORT=8000
MCP_ENABLE_DEBUG_LOG=true
EOF
            log_success "开发配置创建完成"
        fi
        
        # 启动开发服务器
        log_info "启动开发服务器..."
        log_info "访问地址: http://127.0.0.1:8000"
        log_info "API文档: http://127.0.0.1:8000/docs"
        log_info "按 Ctrl+C 停止服务"
        
        export $(cat .env.dev | xargs)
        python main.py
        exit 0
        ;;
    "")
        # 默认执行完整部署
        main
        ;;
    *)
        log_error "未知选项: $1"
        log_info "使用 $0 --help 查看帮助"
        exit 1
        ;;
esac

