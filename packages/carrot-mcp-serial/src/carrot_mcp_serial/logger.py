"""History logger — external observer for Channel events.

Decouples history recording from Channel internals.
Attach to any Channel to record operation history.
"""

from collections import deque

from .channel import Channel, ChannelEvent


class HistoryLogger:
    """Records Channel events as operation history.

    Usage:
        logger = HistoryLogger(max_entries=100)
        channel.attach(logger.on_event)
        # ... later ...
        entries = logger.get_entries()
    """

    def __init__(self, max_entries: int = 100):
        self._entries: deque[dict] = deque(maxlen=max_entries)

    def on_event(self, event: ChannelEvent) -> None:
        """Callback for Channel event notifications."""
        self._entries.append(event.to_dict())

    def get_entries(self, limit: int | None = None) -> list[dict]:
        """Return history entries. Returns all if limit is None."""
        if limit is None:
            return list(self._entries)
        return list(self._entries)[-limit:]

    def clear(self) -> None:
        """Clear all history entries."""
        self._entries.clear()
