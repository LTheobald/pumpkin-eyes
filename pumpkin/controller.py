"""Hardware-independent behaviour, driven by an injected monotonic time."""
from enum import StrEnum


class State(StrEnum):
    SLEEPING = "sleeping"
    WAKING = "waking"
    AWAKE = "awake"
    CLOSING = "closing"


class Controller:
    transition_seconds = 0.7

    def __init__(self, sleep_after=20.0):
        if sleep_after <= 0:
            raise ValueError("sleep_after must be positive")
        self.sleep_after = sleep_after
        self.state = State.SLEEPING
        self.changed_at = 0.0
        self.inactive_since = None
        self.start_open = 0.0

    def openness(self, now):
        elapsed = max(0, min(1, (now - self.changed_at) / self.transition_seconds))
        smooth = elapsed * elapsed * (3 - 2 * elapsed)
        if self.state == State.WAKING:
            return self.start_open + (1 - self.start_open) * smooth
        if self.state == State.CLOSING:
            return self.start_open * (1 - smooth)
        return float(self.state == State.AWAKE)

    def _transition(self, state, now):
        self.start_open = self.openness(now)
        self.state = state
        self.changed_at = now

    def update(self, now, motion):
        """Return True exactly once per new visit. High input prevents sleep."""
        if motion:
            self.inactive_since = None
        elif self.inactive_since is None:
            self.inactive_since = now
        if motion and self.state in (State.SLEEPING, State.CLOSING):
            self._transition(State.WAKING, now)
            return True
        if self.state == State.WAKING and now - self.changed_at >= self.transition_seconds:
            self._transition(State.AWAKE, now)
        if (self.state in (State.WAKING, State.AWAKE)
                and self.inactive_since is not None
                and now - self.inactive_since >= self.sleep_after):
            self._transition(State.CLOSING, now)
        if self.state == State.CLOSING and now - self.changed_at >= self.transition_seconds:
            self._transition(State.SLEEPING, now)
        return False

    def remaining(self, now):
        if self.state in (State.SLEEPING, State.CLOSING):
            return 0.0
        if self.inactive_since is None:
            return self.sleep_after
        return max(0, self.sleep_after - (now - self.inactive_since))
