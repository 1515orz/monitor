import json
from unittest.mock import patch

import numpy as np
import pytest

from modules.monitor import video_stream


@pytest.fixture(autouse=True)
def reset_state():
    video_stream._zmq_connected = False
    video_stream._fps = 0.0
    video_stream._frame_times = []
    yield
    video_stream._zmq_connected = False
    video_stream._fps = 0.0
    video_stream._frame_times = []


def test_get_fps_initial():
    assert video_stream.get_fps() == 0.0


def test_is_connected_initial():
    assert video_stream.is_connected() is False


def test_overlay_bboxes_draws_green_rectangle():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = video_stream._overlay_bboxes(frame, [[10, 20, 100, 200]])
    # Top edge of bbox: row=20, col between 10..100, green channel should be 255
    assert result[20, 10, 1] == 255


def test_overlay_bboxes_empty_list_unchanged():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = video_stream._overlay_bboxes(frame, [])
    assert np.array_equal(result, frame)


def test_encode_mjpeg_returns_bytes():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = video_stream._encode_mjpeg(frame)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_get_bboxes_returns_empty_when_redis_unavailable():
    with patch("modules.monitor.video_stream.redis.Redis") as mock_redis:
        mock_redis.return_value.get.side_effect = Exception("unavailable")
        result = video_stream._get_bboxes()
    assert result == []


def test_get_bboxes_returns_empty_when_no_data():
    with patch("modules.monitor.video_stream.redis.Redis") as mock_redis:
        mock_redis.return_value.get.return_value = None
        result = video_stream._get_bboxes()
    assert result == []


def test_get_bboxes_parses_scene_graph():
    scene = {
        "objects": [
            {"label": "cup", "bbox_2d": [10, 20, 100, 200]},
            {"label": "book", "bbox_2d": [150, 50, 300, 250]},
        ]
    }
    with patch("modules.monitor.video_stream.redis.Redis") as mock_redis:
        mock_redis.return_value.get.return_value = json.dumps(scene).encode()
        result = video_stream._get_bboxes()
    assert result == [[10, 20, 100, 200], [150, 50, 300, 250]]


def test_no_signal_frame_correct_shape():
    frame = video_stream._no_signal_frame()
    assert frame.shape == (480, 640, 3)
