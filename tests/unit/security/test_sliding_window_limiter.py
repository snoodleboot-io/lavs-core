"""Unit tests for :class:`SlidingWindowLimiter`."""

from app.security.sliding_window_limiter import SlidingWindowLimiter


class FakeClock:
    """A manually advanced monotonic clock for deterministic window tests."""

    def __init__(self) -> None:
        """Start the clock at zero."""
        self.now: float = 0.0

    def __call__(self) -> float:
        """Return the current fake time."""
        return self.now

    def advance(self, seconds: float) -> None:
        """Move the clock forward.

        Args:
            seconds: How far to advance.
        """
        self.now += seconds


class TestBudget:
    """Admission within and beyond the per-key budget."""

    def test_admits_up_to_limit_then_refuses(self) -> None:
        """Exactly ``limit`` requests are admitted inside one window."""
        # Arrange
        clock = FakeClock()
        limiter = SlidingWindowLimiter(clock=clock)

        # Act
        outcomes = [limiter.allow("1.2.3.4", limit=3, window_seconds=60) for _ in range(5)]

        # Assert
        assert outcomes == [True, True, True, False, False]

    def test_window_roll_over_restores_budget(self) -> None:
        """Once earlier admissions leave the window the key is admitted again."""
        # Arrange
        clock = FakeClock()
        limiter = SlidingWindowLimiter(clock=clock)
        for _ in range(3):
            assert limiter.allow("1.2.3.4", limit=3, window_seconds=60)
        assert not limiter.allow("1.2.3.4", limit=3, window_seconds=60)

        # Act
        clock.advance(61)
        admitted_after_window = limiter.allow("1.2.3.4", limit=3, window_seconds=60)

        # Assert
        assert admitted_after_window is True

    def test_partial_roll_over_frees_only_expired_slots(self) -> None:
        """The window slides: only admissions older than it stop counting."""
        # Arrange
        clock = FakeClock()
        limiter = SlidingWindowLimiter(clock=clock)
        assert limiter.allow("k", limit=2, window_seconds=60)
        clock.advance(45)
        assert limiter.allow("k", limit=2, window_seconds=60)
        assert not limiter.allow("k", limit=2, window_seconds=60)

        # Act — first admission (t=0) leaves the window at t>60; second (t=45) has not.
        clock.advance(20)
        third = limiter.allow("k", limit=2, window_seconds=60)
        fourth = limiter.allow("k", limit=2, window_seconds=60)

        # Assert
        assert third is True
        assert fourth is False

    def test_per_key_isolation(self) -> None:
        """One exhausted key never affects another key's budget."""
        # Arrange
        clock = FakeClock()
        limiter = SlidingWindowLimiter(clock=clock)
        for _ in range(2):
            assert limiter.allow("10.0.0.1", limit=2, window_seconds=60)
        assert not limiter.allow("10.0.0.1", limit=2, window_seconds=60)

        # Act
        other_admitted = limiter.allow("10.0.0.2", limit=2, window_seconds=60)

        # Assert
        assert other_admitted is True

    def test_non_positive_limit_admits_everything(self) -> None:
        """A limit of 0 (disabled) admits without recording anything."""
        # Arrange
        clock = FakeClock()
        limiter = SlidingWindowLimiter(clock=clock)

        # Act
        outcomes = [limiter.allow("1.2.3.4", limit=0, window_seconds=60) for _ in range(10)]

        # Assert
        assert all(outcomes)
        assert limiter.tracked_key_count == 0


class TestMemoryBound:
    """The tracked-key set never exceeds ``max_keys``."""

    def test_stale_keys_are_pruned_at_the_cap(self) -> None:
        """Keys whose admissions expired are dropped before evicting live ones."""
        # Arrange
        clock = FakeClock()
        limiter = SlidingWindowLimiter(max_keys=3, clock=clock)
        for index in range(3):
            assert limiter.allow(f"stale-{index}", limit=5, window_seconds=60)
        clock.advance(61)

        # Act
        admitted = limiter.allow("fresh", limit=5, window_seconds=60)

        # Assert — all three stale buckets were pruned, only the fresh key remains.
        assert admitted is True
        assert limiter.tracked_key_count == 1

    def test_live_key_evicted_when_cap_exceeded(self) -> None:
        """When every bucket is live, the least recently admitted key is evicted."""
        # Arrange
        clock = FakeClock()
        limiter = SlidingWindowLimiter(max_keys=2, clock=clock)
        assert limiter.allow("oldest", limit=5, window_seconds=60)
        clock.advance(1)
        assert limiter.allow("newer", limit=5, window_seconds=60)
        clock.advance(1)

        # Act
        admitted = limiter.allow("newest", limit=5, window_seconds=60)

        # Assert — cap held at 2; the evicted key is the least recently seen.
        assert admitted is True
        assert limiter.tracked_key_count == 2

    def test_cap_holds_under_many_distinct_keys(self) -> None:
        """Hammering with unique keys never grows the map past the cap."""
        # Arrange
        clock = FakeClock()
        limiter = SlidingWindowLimiter(max_keys=8, clock=clock)

        # Act
        for index in range(100):
            limiter.allow(f"attacker-{index}", limit=5, window_seconds=60)

        # Assert
        assert limiter.tracked_key_count <= 8
