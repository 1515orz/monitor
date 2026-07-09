#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

PORT="${PORT:-18080}"
ZMQ_PORT="${ZMQ_PORT:-15555}"

kill_own() {
    local port=$1 pattern=$2
    local pids
    pids=$(lsof -ti :"$port" 2>/dev/null) || true
    for pid in $pids; do
        if ps -p "$pid" -o args= 2>/dev/null | grep -q "$pattern"; then
            kill "$pid" 2>/dev/null || true
        fi
    done
}

stop_services() {
    kill_own "$PORT" "monitor.server"
    kill_own "$ZMQ_PORT" "test_cam_pub"
}

if [ "${1:-}" = "stop" ]; then
    stop_services
    echo "已停止"
    exit 0
fi

stop_services
sleep 0.5

cleanup() {
    stop_services
}
trap cleanup EXIT INT TERM

echo "启动摄像头推流 (zmq:$ZMQ_PORT)..."
ZMQ_BIND_PORT="$ZMQ_PORT" python3 Monitor/scripts/test_cam_pub.py &

echo "启动 Web 服务 (http:$PORT)..."
cd Monitor
ZMQ_CAMERA_ADDR="tcp://localhost:$ZMQ_PORT" \
python3 -m uvicorn modules.monitor.server:app --host 0.0.0.0 --port "$PORT" &
cd ..

echo "Monitor 已启动 → http://$(hostname -I | awk '{print $1}'):$PORT"
echo "停止服务: ./start.sh stop"
wait
