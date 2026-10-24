"""Block until the database accepts connections. Used by the Docker entrypoint."""

import asyncio
import sys

from sqlalchemy import text

from app.core.db import engine


async def wait_for_db(timeout_s: float = 90, interval_s: float = 2) -> bool:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while True:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("select 1"))
            return True
        except Exception as exc:
            if loop.time() >= deadline:
                print(f"Database not reachable after {timeout_s:.0f}s: {exc}", file=sys.stderr)
                return False
            print("Waiting for database...", file=sys.stderr)
            await asyncio.sleep(interval_s)
        finally:
            await engine.dispose()


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(wait_for_db()) else 1)
