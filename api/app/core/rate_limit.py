"""Small in-process rate limiter (fixed window).

Enough for a single API instance on the free tier; with several instances this would
move to Redis. Used for login and OTP endpoints (SPEC §5.2).
"""

import time
from collections import defaultdict

from app.core.errors import TooManyRequests


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def hit(self, key: str) -> None:
        """Record one attempt for `key`; raise TooManyRequests when over the limit."""
        now = time.monotonic()
        window_start = now - self.window_seconds
        recent = [stamp for stamp in self._hits[key] if stamp > window_start]
        if len(recent) >= self.limit:
            retry_after = int(recent[0] + self.window_seconds - now) + 1
            raise TooManyRequests(
                "Too many attempts, please wait a moment",
                details={"retry_after_seconds": retry_after},
            )
        recent.append(now)
        self._hits[key] = recent

    def reset(self) -> None:
        self._hits.clear()
