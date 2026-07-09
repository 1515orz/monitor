#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

PIDFILE=".monitor.pid"
PORT="${PORT:-8080}"

stop_services() {
    if [ -f "$PIDFILE" ]; then
        while read -r pid; do
            kill "$pid" 2>/dev/null
        done < "$PIDFILE"
        rm -f "$PIDFILE"
        echo "已停止"
    else
        echo "没有运行中的服务"
    fi
}

if [ "${1:-}" = "stop" ]; then
    stop_services
    exit 0
fi

# 如果已在运行，先停掉
if [ -f "$PIDFILE" ]; then
    echo "检测到已有服务运行，先停止..."
    stop_services
    sleep 1
fi

cleanup() {
    stop_services
}
trap cleanup EXIT INT TERM

echo "启动摄像头推流..."
python3 Monitor/scripts/test_cam_pub.py &
echo $! >> "$PIDFILE"

echo "启动 Web 服务 (port $PORT)..."
python3 -m uvicorn Monitor.modules.monitor.server:app --host 0.0.0.0 --port "$PORT" &
echo $! >> "$PIDFILE"

echo "Monitor 已启动 → http://$(hostname -I | awk '{print $1}'):$PORT"
echo "停止服务: ./start.sh stop"
wait
