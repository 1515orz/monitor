import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class SourceEntry:
    key: str
    fetcher: Callable
    interval: float
    cached_value: Any = None
    task: asyncio.Task = field(default=None, repr=False, init=False)

    async def _refresh_loop(self) -> None:
        while True:
            try:
                if asyncio.iscoroutinefunction(self.fetcher):
                    result = await self.fetcher()
                else:
                    result = await asyncio.to_thread(self.fetcher)
                self.cached_value = result
            except Exception:
                logger.exception("fetcher '%s' raised an error; cached value unchanged", self.key)
            await asyncio.sleep(self.interval)

    def start(self) -> None:
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self._refresh_loop())

    def stop(self) -> None:
        if self.task:
            self.task.cancel()


class StateRegistry:
    _sources: dict[str, SourceEntry] = {}

    @classmethod
    def register(cls, key: str, fetcher: Callable, interval: float) -> None:
        if key in cls._sources and cls._sources[key].task is not None:
            cls._sources[key].stop()
        cls._sources[key] = SourceEntry(key=key, fetcher=fetcher, interval=interval)

    @classmethod
    async def start_all(cls) -> None:
        for entry in cls._sources.values():
            entry.start()

    @classmethod
    def snapshot(cls) -> dict[str, Any]:
        return {k: s.cached_value for k, s in cls._sources.items()}

    @classmethod
    async def stop_all(cls) -> None:
        tasks = [e.task for e in cls._sources.values() if e.task is not None]
        for entry in cls._sources.values():
            entry.stop()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        cls._sources.clear()
