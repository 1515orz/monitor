import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from modules.monitor import video_stream
from modules.monitor.sources.system import fetch_system_status
from modules.monitor.state_registry import StateRegistry
from modules.monitor.video_stream import generate_mjpeg

STATIC_DIR = Path(__file__).parent / "static"
WS_PUSH_INTERVAL = float(os.getenv("WS_PUSH_INTERVAL", "0.2"))

StateRegistry.register("system", fetch_system_status, interval=0.5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await StateRegistry.start_all()
    yield
    await StateRegistry.stop_all()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(
        generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class BboxRequest(BaseModel):
    enabled: bool


@app.post("/api/bbox")
async def set_bbox(req: BboxRequest):
    video_stream.set_show_bboxes(req.enabled)
    return JSONResponse({"enabled": req.enabled})


@app.websocket("/ws/state")
async def ws_state(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_text(json.dumps(StateRegistry.snapshot()))
            await asyncio.sleep(WS_PUSH_INTERVAL)
    except WebSocketDisconnect:
        pass
