import os

import cv2
import zmq

def gst_pipeline(sensor_id=0, width=640, height=480, fps=30):
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM), width={width}, height={height}, "
        f"framerate={fps}/1 ! "
        f"nvvidconv ! video/x-raw, format=BGRx ! "
        f"videoconvert ! video/x-raw, format=BGR ! "
        f"appsink max-buffers=1 drop=1"
    )

WIDTH, HEIGHT = 640, 480

ctx = zmq.Context()
sock = ctx.socket(zmq.PUB)
sock.set_hwm(1)
sock.bind(f"tcp://0.0.0.0:{os.getenv('ZMQ_BIND_PORT', '15555')}")

cap = cv2.VideoCapture(gst_pipeline(), cv2.CAP_GSTREAMER)
if not cap.isOpened():
    print("摄像头打开失败")
    exit(1)

print(f"推流中 {WIDTH}x{HEIGHT} @ 30fps (raw BGR)...")
while True:
    ret, frame = cap.read()
    if ret:
        # 发送原始 BGR bytes，省去 JPEG 编解码
        sock.send(frame.tobytes())
