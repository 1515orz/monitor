import asyncio
import os
import time
from threading import Lock
from typing import AsyncIterator

import cv2
import numpy as np
import zmq
import zmq.asyncio
from ultralytics import YOLO

ZMQ_CAMERA_ADDR = os.getenv("ZMQ_CAMERA_ADDR", "tcp://localhost:5555")
MODEL_PATH = os.getenv("YOLO_MODEL", "/home/beng/Desktop/yolov8n.pt")
FRAME_W = int(os.getenv("FRAME_W", "640"))
FRAME_H = int(os.getenv("FRAME_H", "480"))

_zmq_connected: bool = False
_fps: float = 0.0
_frame_times: list[float] = []
_lock = Lock()
_show_bboxes: bool = True

_model = YOLO(MODEL_PATH)


def get_fps() -> float:
    return _fps


def is_connected() -> bool:
    return _zmq_connected


def set_show_bboxes(enabled: bool) -> None:
    global _show_bboxes
    _show_bboxes = enabled


def get_show_bboxes() -> bool:
    return _show_bboxes


def _update_fps() -> None:
    global _fps, _frame_times
    now = time.time()
    with _lock:
        _frame_times = [t for t in _frame_times if now - t < 1.0]
        _frame_times.append(now)
        _fps = float(len(_frame_times))


def _detect_and_draw(frame: np.ndarray) -> np.ndarray:
    results = _model(frame, imgsz=320, verbose=False)
    return results[0].plot()


def _encode_mjpeg(frame: np.ndarray) -> bytes:
    _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return jpeg.tobytes()


def _no_signal_frame() -> np.ndarray:
    frame = np.zeros((FRAME_H, FRAME_W, 3), dtype=np.uint8)
    cv2.putText(frame, "No Signal", (220, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (200, 200, 200), 2)
    return frame


async def generate_mjpeg() -> AsyncIterator[bytes]:
    global _zmq_connected
    ctx = zmq.asyncio.Context()
    sock = ctx.socket(zmq.SUB)
    sock.set_hwm(1)
    sock.connect(ZMQ_CAMERA_ADDR)
    sock.subscribe(b"")
    _zmq_connected = True

    try:
        while True:
            events = await sock.poll(timeout=1000)
            if events:
                msg = await sock.recv()
                # 直接从原始 BGR bytes 重建 numpy array，无需 JPEG 解码
                frame = np.frombuffer(msg, dtype=np.uint8).reshape(FRAME_H, FRAME_W, 3)
                _update_fps()
                if _show_bboxes:
                    frame = await asyncio.to_thread(_detect_and_draw, frame)
            else:
                _zmq_connected = False
                frame = _no_signal_frame()

            jpeg = _encode_mjpeg(frame)
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
    finally:
        sock.close()
        ctx.destroy()
        _zmq_connected = False
