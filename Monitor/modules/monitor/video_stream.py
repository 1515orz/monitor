import json
import os
import time
from threading import Lock
from typing import AsyncIterator

import cv2
import numpy as np
import redis
import zmq
import zmq.asyncio

ZMQ_CAMERA_ADDR = os.getenv("ZMQ_CAMERA_ADDR", "tcp://localhost:5555")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

_zmq_connected: bool = False
_fps: float = 0.0
_frame_times: list[float] = []
_lock = Lock()


def get_fps() -> float:
    return _fps


def is_connected() -> bool:
    return _zmq_connected


def _update_fps() -> None:
    global _fps, _frame_times
    now = time.time()
    with _lock:
        _frame_times = [t for t in _frame_times if now - t < 1.0]
        _frame_times.append(now)
        _fps = float(len(_frame_times))


def _get_bboxes() -> list:
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_connect_timeout=0.5)
        data = r.get("scene:current")
        if data is None:
            return []
        scene = json.loads(data)
        return [obj["bbox_2d"] for obj in scene.get("objects", []) if "bbox_2d" in obj]
    except Exception:
        return []


def _overlay_bboxes(frame: np.ndarray, bboxes: list) -> np.ndarray:
    for bbox in bboxes:
        x1, y1, x2, y2 = bbox
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    return frame


def _encode_mjpeg(frame: np.ndarray) -> bytes:
    _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return jpeg.tobytes()


def _no_signal_frame() -> np.ndarray:
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, "No Signal", (220, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (200, 200, 200), 2)
    return frame


async def generate_mjpeg() -> AsyncIterator[bytes]:
    global _zmq_connected
    ctx = zmq.asyncio.Context()
    sock = ctx.socket(zmq.SUB)
    sock.connect(ZMQ_CAMERA_ADDR)
    sock.subscribe(b"")
    _zmq_connected = True

    try:
        while True:
            events = await sock.poll(timeout=1000)  # 1s timeout
            if events:
                msg = await sock.recv()
                frame = cv2.imdecode(np.frombuffer(msg, np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    frame = _no_signal_frame()
                else:
                    _update_fps()
                    frame = _overlay_bboxes(frame, _get_bboxes())
            else:
                _zmq_connected = False
                frame = _no_signal_frame()

            jpeg = _encode_mjpeg(frame)
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
    finally:
        sock.close()
        ctx.destroy()
        _zmq_connected = False
