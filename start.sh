#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

PORT="${PORT:-8080}"

cleanup() {
    echo "正在停止..."
    kill $CAM_PID $WEB_PID 2>/dev/null
    wait $CAM_PID $WEB_PID 2>/dev/null
    echo "已停止"
}
trap cleanup EXIT INT TERM

echo "启动摄像头推流..."
python3 Monitor/scripts/test_cam_pub.py &
CAM_PID=$!

echo "启动 Web 服务 (port $PORT)..."
python3 -m uvicorn Monitor.modules.monitor.server:app --host 0.0.0.0 --port "$PORT" &
WEB_PID=$!

echo "Monitor 已启动 → http://$(hostname -I | awk '{print $1}'):$PORT"
wait
