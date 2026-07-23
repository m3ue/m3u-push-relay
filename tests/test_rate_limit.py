from rate_limit import RateLimiter


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_allows_up_to_max_events_within_window():
    limiter = RateLimiter(max_events=3, window_seconds=60)

    assert limiter.allow("key") is True
    assert limiter.allow("key") is True
    assert limiter.allow("key") is True
    assert limiter.allow("key") is False


def test_different_keys_have_independent_buckets():
    limiter = RateLimiter(max_events=1, window_seconds=60)

    assert limiter.allow("a") is True
    assert limiter.allow("b") is True
    assert limiter.allow("a") is False
    assert limiter.allow("b") is False


def test_events_expire_after_the_window(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr("rate_limit.time.monotonic", lambda: clock.now)

    limiter = RateLimiter(max_events=1, window_seconds=10)

    assert limiter.allow("key") is True
    assert limiter.allow("key") is False

    clock.advance(10.01)

    assert limiter.allow("key") is True
