#!/bin/bash

# CII Intraday Service Startup Script
# Sử dụng để chạy service trong background

SERVICE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="cii_intraday_service"
LOG_FILE="$SERVICE_DIR/logs/service.log"
PID_FILE="$SERVICE_DIR/logs/service.pid"

# Tạo thư mục logs nếu chưa có
mkdir -p "$SERVICE_DIR/logs"

# Hàm kiểm tra service có đang chạy không
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Hàm khởi động service
start_service() {
    if is_running; then
        echo "Service $SERVICE_NAME đã đang chạy (PID: $(cat $PID_FILE))"
        return 1
    fi
    
    echo "Đang khởi động $SERVICE_NAME..."
    
    # Chạy service trong background
    cd "$SERVICE_DIR"
    nohup python run_service.py > "$LOG_FILE" 2>&1 &
    PID=$!
    
    # Lưu PID
    echo $PID > "$PID_FILE"
    
    # Chờ một chút để kiểm tra
    sleep 2
    
    if is_running; then
        echo "✅ Service $SERVICE_NAME đã khởi động thành công (PID: $PID)"
        echo "📝 Log file: $LOG_FILE"
        echo "🔄 Để dừng service: $0 stop"
        return 0
    else
        echo "❌ Không thể khởi động service"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Hàm dừng service
stop_service() {
    if ! is_running; then
        echo "Service $SERVICE_NAME không đang chạy"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    echo "Đang dừng service $SERVICE_NAME (PID: $PID)..."
    
    # Gửi tín hiệu SIGTERM
    kill -TERM "$PID"
    
    # Chờ service dừng
    for i in {1..10}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    
    # Nếu vẫn chạy, force kill
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Force killing service..."
        kill -KILL "$PID"
    fi
    
    rm -f "$PID_FILE"
    echo "✅ Service $SERVICE_NAME đã dừng"
}

# Hàm kiểm tra trạng thái
status_service() {
    if is_running; then
        PID=$(cat "$PID_FILE")
        echo "✅ Service $SERVICE_NAME đang chạy (PID: $PID)"
        echo "📝 Log file: $LOG_FILE"
        
        # Hiển thị thông tin process
        echo "📊 Process info:"
        ps -p "$PID" -o pid,ppid,cmd,etime,pcpu,pmem
        
        # Hiển thị log cuối cùng
        echo "📋 Recent logs:"
        tail -5 "$LOG_FILE"
    else
        echo "❌ Service $SERVICE_NAME không đang chạy"
    fi
}

# Hàm restart service
restart_service() {
    stop_service
    sleep 2
    start_service
}

# Hàm xem log
view_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo "📝 Viewing logs from $LOG_FILE:"
        echo "Press Ctrl+C to exit"
        tail -f "$LOG_FILE"
    else
        echo "❌ Log file không tồn tại: $LOG_FILE"
    fi
}

# Hàm hiển thị help
show_help() {
    echo "CII Intraday Service Management Script"
    echo ""
    echo "Usage: $0 {start|stop|restart|status|logs|help}"
    echo ""
    echo "Commands:"
    echo "  start   - Khởi động service"
    echo "  stop    - Dừng service"
    echo "  restart - Khởi động lại service"
    echo "  status  - Kiểm tra trạng thái service"
    echo "  logs    - Xem log real-time"
    echo "  help    - Hiển thị help này"
    echo ""
    echo "Files:"
    echo "  Service dir: $SERVICE_DIR"
    echo "  Log file:    $LOG_FILE"
    echo "  PID file:    $PID_FILE"
}

# Main script
case "$1" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        status_service
        ;;
    logs)
        view_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ Lệnh không hợp lệ: $1"
        echo ""
        show_help
        exit 1
        ;;
esac

exit $?
