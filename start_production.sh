#!/bin/bash

# Google Drive CRM Production Startup Script
# This script starts all necessary services for production deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="Google Drive CRM"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/venv"
LOG_DIR="$APP_DIR/logs"
PID_DIR="$APP_DIR/pids"

# Create necessary directories
mkdir -p "$LOG_DIR" "$PID_DIR"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if service is running
is_service_running() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

# Function to start service
start_service() {
    local service_name=$1
    local command=$2
    local pid_file="$PID_DIR/${service_name}.pid"
    local log_file="$LOG_DIR/${service_name}.log"
    
    if is_service_running "$service_name"; then
        print_warning "$service_name is already running (PID: $(cat "$pid_file"))"
        return 0
    fi
    
    print_status "Starting $service_name..."
    
    # Start service in background
    nohup $command > "$log_file" 2>&1 &
    local pid=$!
    
    # Save PID
    echo "$pid" > "$pid_file"
    
    # Wait a moment to check if service started successfully
    sleep 2
    if ps -p "$pid" > /dev/null 2>&1; then
        print_status "$service_name started successfully (PID: $pid)"
        return 0
    else
        print_error "Failed to start $service_name"
        rm -f "$pid_file"
        return 1
    fi
}

# Function to stop service
stop_service() {
    local service_name=$1
    local pid_file="$PID_DIR/${service_name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            print_status "Stopping $service_name (PID: $pid)..."
            kill "$pid"
            
            # Wait for service to stop
            local count=0
            while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            if ps -p "$pid" > /dev/null 2>&1; then
                print_warning "Force killing $service_name..."
                kill -9 "$pid"
            fi
            
            rm -f "$pid_file"
            print_status "$service_name stopped"
        else
            print_warning "$service_name is not running"
            rm -f "$pid_file"
        fi
    else
        print_warning "$service_name is not running"
    fi
}

# Function to check dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    # Check Python virtual environment
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Python virtual environment not found. Please run: python3 -m venv venv"
        exit 1
    fi
    
    # Check if virtual environment is activated
    if [ -z "$VIRTUAL_ENV" ]; then
        print_status "Activating virtual environment..."
        source "$VENV_DIR/bin/activate"
    fi
    
    # Check required packages
    local missing_packages=()
    for package in "gunicorn" "celery" "redis" "flask"; do
        if ! python -c "import $package" 2>/dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        print_error "Missing packages: ${missing_packages[*]}"
        print_status "Installing missing packages..."
        pip install "${missing_packages[@]}"
    fi
    
    # Check Redis connection
    if ! redis-cli ping > /dev/null 2>&1; then
        print_error "Redis is not running. Please start Redis first."
        exit 1
    fi
    
    # Check MongoDB connection
    if ! python -c "from pymongo import MongoClient; MongoClient('mongodb://localhost:27017').admin.command('ping')" 2>/dev/null; then
        print_error "MongoDB is not running. Please start MongoDB first."
        exit 1
    fi
    
    print_status "All dependencies are satisfied"
}

# Function to start all services
start_all_services() {
    print_status "Starting $APP_NAME production services..."
    
    # Check dependencies first
    check_dependencies
    
    # Start Celery worker
    start_service "celery-worker" "celery -A app.services.background_tasks.celery_app worker --loglevel=info --concurrency=4"
    
    # Start Celery beat (scheduler)
    start_service "celery-beat" "celery -A app.services.background_tasks.celery_app beat --loglevel=info"
    
    # Start Gunicorn application server
    start_service "gunicorn" "gunicorn -c gunicorn_config.py run_production:app"
    
    print_status "All services started successfully!"
    print_status "Application is running on http://localhost:5000"
    print_status "Check logs in: $LOG_DIR"
    print_status "Check PIDs in: $PID_DIR"
}

# Function to stop all services
stop_all_services() {
    print_status "Stopping $APP_NAME production services..."
    
    stop_service "gunicorn"
    stop_service "celery-beat"
    stop_service "celery-worker"
    
    print_status "All services stopped!"
}

# Function to restart all services
restart_all_services() {
    print_status "Restarting $APP_NAME production services..."
    stop_all_services
    sleep 2
    start_all_services
}

# Function to show status
show_status() {
    print_status "Service Status:"
    echo "=================="
    
    local services=("gunicorn" "celery-worker" "celery-beat")
    
    for service in "${services[@]}"; do
        if is_service_running "$service"; then
            local pid=$(cat "$PID_DIR/${service}.pid")
            echo -e "${GREEN}✓${NC} $service: Running (PID: $pid)"
        else
            echo -e "${RED}✗${NC} $service: Not running"
        fi
    done
    
    echo ""
    print_status "Log files:"
    ls -la "$LOG_DIR" 2>/dev/null || echo "No log files found"
    
    echo ""
    print_status "PID files:"
    ls -la "$PID_DIR" 2>/dev/null || echo "No PID files found"
}

# Function to show logs
show_logs() {
    local service_name=$1
    local log_file="$LOG_DIR/${service_name}.log"
    
    if [ -z "$service_name" ]; then
        print_error "Please specify a service name (gunicorn, celery-worker, celery-beat)"
        exit 1
    fi
    
    if [ -f "$log_file" ]; then
        print_status "Showing logs for $service_name:"
        tail -f "$log_file"
    else
        print_error "Log file not found: $log_file"
        exit 1
    fi
}

# Function to show help
show_help() {
    echo "Usage: $0 {start|stop|restart|status|logs|help}"
    echo ""
    echo "Commands:"
    echo "  start     Start all production services"
    echo "  stop      Stop all production services"
    echo "  restart   Restart all production services"
    echo "  status    Show status of all services"
    echo "  logs      Show logs for a specific service"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start                    # Start all services"
    echo "  $0 logs gunicorn           # Show Gunicorn logs"
    echo "  $0 status                  # Show service status"
}

# Main script logic
case "$1" in
    start)
        start_all_services
        ;;
    stop)
        stop_all_services
        ;;
    restart)
        restart_all_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac

exit 0
