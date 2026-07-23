import time
from collections import defaultdict, deque


class RateLimiter:
    """In-memory sliding-window rate limiter.

    Single-process only (no shared store) - fine for a single Render instance,
    matches the existing in-process app.state usage elsewhere in this app.
    Exists as defense-in-depth for a shared-secret model where the secret is
    baked into publicly-distributed self-hosted app images and can't be kept
    truly private: this bounds how much damage a "known" secret can do.
    """

    def __init__(self, max_events: int, window_seconds: float):
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        events = self._events[key]

        while events and events[0] <= now - self.window_seconds:
            events.popleft()

        if len(events) >= self.max_events:
            return False

        events.append(now)
        return True
