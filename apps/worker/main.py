from __future__ import annotations

import asyncio
import logging
import signal

from packages.domain.config import get_settings
from packages.domain.database import close_db, init_db

logger = logging.getLogger(__name__)


class Worker:
    def __init__(self):
        self._running = False
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        settings = get_settings()
        await init_db()
        self._running = True
        logger.info("Worker started in %s mode", settings.app_env)

        # Register signal handlers if supported (not available on Windows)
        import sys

        if sys.platform != "win32":
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                try:
                    loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
                except NotImplementedError:
                    pass

        # Keep running
        while self._running:
            await asyncio.sleep(1)

    async def stop(self) -> None:
        logger.info("Worker stopping...")
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await close_db()
        logger.info("Worker stopped")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    worker = Worker()
    try:
        await worker.start()
    except KeyboardInterrupt:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
