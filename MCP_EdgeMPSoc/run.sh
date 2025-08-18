#!/bin/bash

# WattMCP Runner Script
# This script helps run different components of the WattMCP system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
MODE=""
COMPONENT=""
DETACHED=false
CLEAN=false

# Help function
show_help() {
    echo "Usage: $0 [OPTIONS] COMMAND"
    echo ""
    echo "Commands:"
    echo "  server      Start MCP server"
    echo "  client      Start edge client"
    echo "  tools       Run AI agent tools demo"
    echo "  test        Run tests"
    echo "  docker      Run with Docker"
    echo "  clean       Clean up containers and volumes"
    echo "  help        Show this help"
    echo ""
    echo "Options:"
    echo "  -d, --detached    Run in detached mode (Docker only)"
    echo "  -c, --clean       Clean before running"
    echo "  -h, --help        Show help"
}

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check dependencies
check_dependencies() {
    local deps=("python3" "pip")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" > /dev/null 2>&1; then
            missing+=("$dep")
        fi
    done
    
    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing[*]}"
        exit 1
    fi
}

# Install Python dependencies
install_deps() {
    log_info "Installing Python dependencies..."
    pip install -r requirements.txt
}

# Start MCP server
start_server() {
    log_info "Starting MCP Server..."
    
    # Check if Redis is running
    if ! pgrep -x "redis-server" > /dev/null; then
        log_warn "Redis not running. Please start Redis server first."
        log_info "You can start Redis with: redis-server"
        exit 1
    fi
    
    # Check if MQTT broker is running
    if ! netstat -tuln | grep -q ":1883"; then
        log_warn "MQTT broker not detected on port 1883"
        log_info "You can start Mosquitto with: mosquitto -c /etc/mosquitto/mosquitto.conf"
    fi
    
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
    python src/mcp_server/mcp_server.py
}

# Start edge client
start_client() {
    log_info "Starting Edge Client..."
    
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
    python src/mcp_client/mcp_client.py
}

# Run AI tools demo
run_tools() {
    log_info "Running AI Agent Tools Demo..."
    
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
    python src/mcp_tools/mcp_tools.py
}

# Run tests
run_tests() {
    log_info "Running tests..."
    
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
    python -m pytest tests/ -v
}

# Docker operations
run_docker() {
    log_info "Starting Docker services..."
    
    if [ "$CLEAN" = true ]; then
        log_info "Cleaning up Docker resources..."
        docker-compose down -v
        docker system prune -f
    fi
    
    if [ "$DETACHED" = true ]; then
        docker-compose up -d
        log_info "Services started in detached mode"
        log_info "View logs: docker-compose logs -f"
    else
        docker-compose up
    fi
}

# Clean up
clean_up() {
    log_info "Cleaning up Docker resources..."
    docker-compose down -v
    docker system prune -f
    log_info "Cleanup complete"
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--detached)
                DETACHED=true
                shift
                ;;
            -c|--clean)
                CLEAN=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            server|client|tools|test|docker|clean|help)
                COMPONENT="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Main function
main() {
    parse_args "$@"
    
    if [ -z "$COMPONENT" ]; then
        show_help
        exit 1
    fi
    
    case $COMPONENT in
        server)
            check_dependencies
            install_deps
            start_server
            ;;
        client)
            check_dependencies
            install_deps
            start_client
            ;;
        tools)
            check_dependencies
            install_deps
            run_tools
            ;;
        test)
            check_dependencies
            install_deps
            run_tests
            ;;
        docker)
            run_docker
            ;;
        clean)
            clean_up
            ;;
        help)
            show_help
            ;;
        *)
            log_error "Unknown component: $COMPONENT"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"