from unittest.mock import patch, MagicMock
from modules.monitor.sources import system as system_module
from modules.monitor.sources.system import fetch_system_status


def test_returns_required_keys():
    system_module._redis_client = MagicMock()
    system_module._redis_client.ping.return_value = True
    with patch("modules.monitor.sources.system.video_stream.get_fps", return_value=25.0):
        with patch("modules.monitor.sources.system.video_stream.is_connected", return_value=True):
            result = fetch_system_status()
    assert set(result.keys()) == {"fps", "redis", "zmq"}


def test_redis_false_when_unavailable():
    system_module._redis_client = MagicMock()
    system_module._redis_client.ping.side_effect = Exception("connection refused")
    with patch("modules.monitor.sources.system.video_stream.get_fps", return_value=0.0):
        with patch("modules.monitor.sources.system.video_stream.is_connected", return_value=False):
            result = fetch_system_status()
    assert result["redis"] is False


def test_redis_true_when_available():
    system_module._redis_client = MagicMock()
    system_module._redis_client.ping.return_value = True
    with patch("modules.monitor.sources.system.video_stream.get_fps", return_value=30.0):
        with patch("modules.monitor.sources.system.video_stream.is_connected", return_value=True):
            result = fetch_system_status()
    assert result["redis"] is True


def test_fps_and_zmq_come_from_video_stream():
    system_module._redis_client = MagicMock()
    system_module._redis_client.ping.return_value = True
    with patch("modules.monitor.sources.system.video_stream.get_fps", return_value=15.5):
        with patch("modules.monitor.sources.system.video_stream.is_connected", return_value=False):
            result = fetch_system_status()
    assert result["fps"] == 15.5
    assert result["zmq"] is False
