import asyncio
import pytest
from modules.monitor.state_registry import StateRegistry


@pytest.fixture(autouse=True)
async def reset_registry():
    yield
    await StateRegistry.stop_all()


async def test_snapshot_returns_none_before_start():
    StateRegistry.register("x", lambda: 1, interval=0.1)
    snap = StateRegistry.snapshot()
    assert snap["x"] is None


async def test_snapshot_after_start_returns_fetched_value():
    StateRegistry.register("x", lambda: 42, interval=0.1)
    await StateRegistry.start_all()
    await asyncio.sleep(0.15)
    assert StateRegistry.snapshot()["x"] == 42


async def test_multiple_sources_are_independent():
    StateRegistry.register("a", lambda: "alpha", interval=0.1)
    StateRegistry.register("b", lambda: "beta", interval=0.1)
    await StateRegistry.start_all()
    await asyncio.sleep(0.15)
    snap = StateRegistry.snapshot()
    assert snap["a"] == "alpha"
    assert snap["b"] == "beta"


async def test_snapshot_reads_cache_not_live_fetch():
    call_count = 0

    def counting_fetcher():
        nonlocal call_count
        call_count += 1
        return call_count

    StateRegistry.register("c", counting_fetcher, interval=10.0)
    await StateRegistry.start_all()
    await asyncio.sleep(0.05)
    StateRegistry.snapshot()
    StateRegistry.snapshot()
    assert call_count == 1  # fetcher called once; snapshot reads cache


async def test_fetcher_exception_keeps_cached_value_as_none():
    def bad_fetcher():
        raise RuntimeError("fail")

    StateRegistry.register("d", bad_fetcher, interval=0.1)
    await StateRegistry.start_all()
    await asyncio.sleep(0.15)
    assert StateRegistry.snapshot()["d"] is None
