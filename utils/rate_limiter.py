"""Per-domain polite rate limiting with jitter. Thread-safe."""
import os
import random
import threading
import time

DEFAULT_INTERVAL = float(os.getenv("RATE_LIMIT_SECONDS", "0.35"))

DOMAIN_INTERVALS = {
    "www.reddit.com": 2.2,
    "www.etsy.com": 2.5,
    "www.walmart.com": 2.5,
    "www.pinterest.com": 2.0,
    "trends.google.com": 3.0,
}


class RateLimiter:
    def __init__(self, default_interval: float = DEFAULT_INTERVAL):
        self.default = default_interval
        self._last = {}
        self._locks = {}
        self._guard = threading.Lock()

    def _lock_for(self, key: str) -> threading.Lock:
        with self._guard:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]

    def wait(self, key: str):
        interval = DOMAIN_INTERVALS.get(key, self.default)
        lock = self._lock_for(key)
        with lock:
            now = time.time()
            elapsed = now - self._last.get(key, 0.0)
            remaining = interval - elapsed
            if remaining > 0:
                time.sleep(remaining + random.uniform(0.0, 0.15))
            self._last[key] = time.time()


limiter = RateLimiter()
