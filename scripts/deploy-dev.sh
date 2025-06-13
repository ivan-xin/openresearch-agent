#!/bin/bash

# Simplified AI Agent Deployment Script

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Get paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
AI_AGENT_DIR="$PROJECT_ROOT"

# Configuration
ENVIRONMENT="${ENVIRONMENT:-development}"
SERVICE_PORT="${PORT:-8000}"

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 is required"
        exit 1
    fi
    
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 is required"
        exit 1
    fi
    
    log_success "Dependencies check passed"
}

# Setup virtual environment
setup_venv() {
    log_info "Setting up virtual environment..."
    
    cd "$AI_AGENT_DIR"
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_success "Virtual environment created"
    fi
    
    source venv/bin/activate
    pip install --upgrade pip
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        log_success "Dependencies installed"
    fi
    
    deactivate
}

# Setup MCP server (based on your .env path)
setup_mcp_server() {
    log_info "Setting up MCP server..."
    
    MCP_SERVER_DIR="$PROJECT_ROOT/../openresearch-mcp-server"
    
    if [ -d "$MCP_SERVER_DIR" ]; then
        cd "$MCP_SERVER_DIR"
        
        if [ ! -d "venv" ]; then
            python3 -m venv venv
        fi
        
        source venv/bin/activate
        pip install --upgrade pip
        
        if [ -f "requirements.txt" ]; then
            pip install -r requirements.txt
            log_success "MCP server dependencies installed"
        fi
        
        deactivate
        
        # Setup MCP server logging
        log_info "Setting up MCP server logging..."
        mkdir -p "$MCP_SERVER_DIR/logs"
        chmod 755 "$MCP_SERVER_DIR/logs"
        
        # Create mcp.log file if it doesn't exist
        if [ ! -f "$MCP_SERVER_DIR/logs/mcp.log" ]; then
            touch "$MCP_SERVER_DIR/logs/mcp.log"
            chmod 644 "$MCP_SERVER_DIR/logs/mcp.log"
            log_success "Created MCP log file: $MCP_SERVER_DIR/logs/mcp.log"
        else
            log_info "MCP log file already exists: $MCP_SERVER_DIR/logs/mcp.log"
        fi
        
        cd "$AI_AGENT_DIR"
    else
        log_warning "MCP server directory not found: $MCP_SERVER_DIR"
        log_info "Expected path: $MCP_SERVER_DIR"
    fi
}


# Setup logging
setup_logging() {
    log_info "Setting up logging..."
    mkdir -p "$AI_AGENT_DIR/logs"
    chmod 755 "$AI_AGENT_DIR/logs"
    log_success "Log directory created"
}

# Verify environment
verify_env() {
    log_info "Verifying environment..."
    
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_error ".env file not found"
        exit 1
    fi
    
    # Check if required variables are set
    source "$PROJECT_ROOT/.env"
    
    if [ -z "$TOGETHER_API_KEY" ]; then
        log_warning "TOGETHER_API_KEY not set"
    fi
    
    log_success "Environment verification completed"
}

# Configuration
ENVIRONMENT="${ENVIRONMENT:-development}"
SERVICE_PORT="${PORT:-8000}"
AUTO_START="${AUTO_START:-false}"

# Start service
start_service() {
    log_info "Starting service..."
    
    cd "$AI_AGENT_DIR"
    
    log_info "Development mode"
    
    if [ "$AUTO_START" = "true" ]; then
        log_info "Auto-starting service..."
        
        # Check if ai-agent directory exists
        if [ ! -d "ai-agent" ]; then
            log_error "ai-agent directory not found in $AI_AGENT_DIR"
            exit 1
        fi
        
        # Check if main.py exists in ai-agent directory
        if [ ! -f "ai-agent/main.py" ]; then
            log_error "main.py not found in $AI_AGENT_DIR/ai-agent"
            exit 1
        fi
        
        source venv/bin/activate
        cd ai-agent
        
        log_success "Service starting on port $SERVICE_PORT..."
        log_info "Press Ctrl+C to stop the service"
        log_info "API docs will be available at: http://localhost:$SERVICE_PORT/docs"
        
        # Start the service
        python main.py
    else
        log_info "To start manually: cd $AI_AGENT_DIR/ai-agent && source ../venv/bin/activate && python main.py"
        log_info "Or run with --start flag to auto-start"
    fi
}

# Main function
main() {
    log_info "Starting simplified AI Agent deployment..."
    
    check_dependencies
    setup_venv
    setup_mcp_server
    setup_logging
    verify_env
    start_service
    
    log_success "Deployment completed!"
    log_info "Service will run on: http://localhost:$SERVICE_PORT"
    log_info "API docs: http://localhost:$SERVICE_PORT/docs"
}

# Help
show_help() {
    echo "Simplified AI Agent Deployment Script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show help"
    echo "  -p, --port PORT     Service port (default: 8000)"
    echo "  -s, --start         Auto-start service after deployment"
    echo ""
    echo "Examples:"
    echo "  $0                  # Development deployment (setup only)"
    echo "  $0 --start          # Development deployment and start service"
}


# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -p|--port)
            SERVICE_PORT="$2"
            shift 2
            ;;
        -s|--start)
            AUTO_START="true"
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

main
