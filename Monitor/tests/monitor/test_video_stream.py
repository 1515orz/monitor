import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from modules.monitor import video_stream


@pytest.fixture(autouse=True)
def reset_state():
    video_stream._zmq_connected = False
    video_stream._fps = 0.0
    video_stream._frame_times = []
    video_stream._model = None
    video_stream._show_bboxes = True
    yield
    video_stream._zmq_connected = False
    video_stream._fps = 0.0
    video_stream._frame_times = []
    video_stream._model = None
    video_stream._show_bboxes = True


# ── 保留的测试 ────────────────────────────────────────────────────────────────

def test_get_fps_initial():
    assert video_stream.get_fps() == 0.0


def test_is_connected_initial():
    assert video_stream.is_connected() is False


def test_encode_mjpeg_returns_bytes():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = video_stream._encode_mjpeg(frame)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_no_signal_frame_correct_shape():
    frame = video_stream._no_signal_frame()
    assert frame.shape == (480, 640, 3)


# ── 新增的测试 ────────────────────────────────────────────────────────────────

def test_detect_and_draw_calls_model_with_frame(monkeypatch):
    mock_model = MagicMock()
    mock_result = MagicMock()
    mock_result.plot.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_model.return_value = [mock_result]
    monkeypatch.setattr(video_stream, "_model", mock_model)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    video_stream._detect_and_draw(frame)

    mock_model.assert_called_once_with(frame, imgsz=320, verbose=False)


def test_detect_and_draw_returns_plotted_frame(monkeypatch):
    expected = np.ones((480, 640, 3), dtype=np.uint8) * 42
    mock_model = MagicMock()
    mock_result = MagicMock()
    mock_result.plot.return_value = expected
    mock_model.return_value = [mock_result]
    monkeypatch.setattr(video_stream, "_model", mock_model)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = video_stream._detect_and_draw(frame)

    assert np.array_equal(result, expected)


def test_detect_and_draw_lazy_loads_on_first_call(monkeypatch):
    monkeypatch.setattr(video_stream, "_model", None)

    mock_instance = MagicMock()
    mock_result = MagicMock()
    mock_result.plot.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_instance.return_value = [mock_result]

    with patch("modules.monitor.video_stream.YOLO", return_value=mock_instance) as mock_yolo_cls:
        assert video_stream._model is None
        video_stream._detect_and_draw(np.zeros((480, 640, 3), dtype=np.uint8))
        mock_yolo_cls.assert_called_once_with(video_stream.MODEL_PATH)
        assert video_stream._model is not None


def test_show_bboxes_toggle():
    assert video_stream.get_show_bboxes() is True
    video_stream.set_show_bboxes(False)
    assert video_stream.get_show_bboxes() is False
    video_stream.set_show_bboxes(True)
    assert video_stream.get_show_bboxes() is True
