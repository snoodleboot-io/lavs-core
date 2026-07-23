"""A stdlib-only, in-process sliding-window rate limiter."""

import time
from collections import deque
from collections.abc import Callable


class SlidingWindowLimiter:
    """A per-key sliding-window-log limiter with a bounded key set.

    Each key (a client IP for the auth middleware) owns a deque of admission
    timestamps; a request is admitted when fewer than ``limit`` admissions fall
    inside the trailing ``window_seconds``. Refused requests are **not**
    recorded, so a blocked client regains its budget as soon as the window
    slides past its earlier admissions.

    Memory bound: at most ``max_keys`` buckets are kept, and each bucket holds
    at most ``limit`` timestamps (stale entries are dropped on every touch), so
    worst-case memory is ``max_keys x limit`` floats. When a new key would
    exceed the cap, buckets whose newest admission has left the window are
    pruned first; if every bucket is still live, the one with the oldest most
    recent admission is evicted.

    The clock is injectable (monotonic by default) so tests can drive window
    roll-over deterministically.
    """

    _DEFAULT_MAX_KEYS: int = 1024

    def __init__(
        self,
        max_keys: int | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        """Initialise an empty limiter.

        Args:
            max_keys: Upper bound on distinct keys tracked at once.
            clock: Monotonic time source returning seconds (injectable for
                tests).
        """
        self._max_keys: int = max_keys if max_keys is not None else self._DEFAULT_MAX_KEYS
        self._clock: Callable[[], float] = clock if clock is not None else time.monotonic
        self._admissions: dict[str, deque[float]] = {}

    @property
    def tracked_key_count(self) -> int:
        """Number of distinct keys currently holding a bucket."""
        return len(self._admissions)

    def allow(self, key: str, limit: int, window_seconds: float) -> bool:
        """Decide whether a request from ``key`` is admitted right now.

        Args:
            key: The client identity (an IP address for the middleware).
            limit: Maximum admissions per key inside the window; a
                non-positive limit admits everything (limiting disabled).
            window_seconds: The trailing window length in seconds.

        Returns:
            ``True`` when the request is admitted (and recorded), ``False``
            when the key has exhausted its budget for the current window.
        """
        if limit <= 0:
            return True

        now = self._clock()
        cutoff = now - window_seconds

        bucket = self._admissions.get(key)
        if bucket is None:
            if len(self._admissions) >= self._max_keys:
                self._prune_stale(cutoff)
            if len(self._admissions) >= self._max_keys:
                self._evict_least_recent()
            bucket = deque()
            self._admissions[key] = bucket

        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= limit:
            return False

        bucket.append(now)
        return True

    def _prune_stale(self, cutoff: float) -> None:
        """Drop every bucket whose newest admission predates ``cutoff``.

        Args:
            cutoff: Timestamps at or before this instant are outside the
                window.
        """
        stale = [key for key, bucket in self._admissions.items() if bucket[-1] <= cutoff]
        for key in stale:
            del self._admissions[key]

    def _evict_least_recent(self) -> None:
        """Evict the key whose most recent admission is oldest."""
        if not self._admissions:
            return
        oldest_key = min(self._admissions, key=self._newest_admission)
        del self._admissions[oldest_key]

    def _newest_admission(self, key: str) -> float:
        """Return the newest admission timestamp recorded for ``key``.

        Args:
            key: A key currently holding a bucket.

        Returns:
            The most recent admission time for the key.
        """
        return self._admissions[key][-1]
