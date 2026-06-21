"""In-memory ring-buffer statistics for the BlackBull demo site.

Uses ``collections.deque`` with a fixed ``maxlen`` to keep the last N
requests in memory.  No database, no file I/O — fits the Alwaysdata
256 MB RAM / 1 GB SSD constraints perfectly.
"""

import time
from collections import deque
from typing import Any, Dict, List


class Stats:
    """Thread-safe-ish ring-buffer statistics collector.

    All mutation happens inside the async middleware on the event loop,
    so no locks are needed for this single-worker demo.
    """

    def __init__(self, maxlen: int = 50) -> None:
        self._requests: deque[Dict[str, Any]] = deque(maxlen=maxlen)
        self._total: int = 0
        self._start_time: float = time.time()
        self._active_connections: int = 0

    # -- Recording -------------------------------------------------------

    def record(
        self,
        *,
        method: str,
        path: str,
        status: int,
        http_version: str,
        elapsed_ms: float,
        user_agent: str = '',
    ) -> None:
        """Record a completed HTTP request."""
        entry: Dict[str, Any] = {
            'time': time.strftime('%H:%M:%S'),
            'method': method,
            'path': path,
            'status': status,
            'http_version': http_version,
            'elapsed_ms': round(elapsed_ms, 2),
            'user_agent': user_agent[:60],
        }
        self._requests.append(entry)
        self._total += 1

    # -- Connection tracking ---------------------------------------------

    def inc_connections(self) -> None:
        self._active_connections += 1

    def dec_connections(self) -> None:
        self._active_connections = max(0, self._active_connections - 1)

    # -- Derived properties ----------------------------------------------

    @property
    def total_requests(self) -> int:
        return self._total

    @property
    def active_connections(self) -> int:
        return self._active_connections

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self._start_time

    @property
    def avg_response_time_ms(self) -> float:
        if not self._requests:
            return 0.0
        total = sum(r['elapsed_ms'] for r in self._requests)
        return round(total / len(self._requests), 2)

    @property
    def recent_requests(self) -> List[Dict[str, Any]]:
        """Return most-recent-first list of recorded requests."""
        return list(reversed(self._requests))

    # -- Export ----------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_requests': self.total_requests,
            'active_connections': self.active_connections,
            'avg_response_time_ms': self.avg_response_time_ms,
            'uptime_seconds': round(self.uptime_seconds, 2),
            'recent_requests': self.recent_requests,
        }


# Module-level singleton — imported by app.py and templates.py.
stats = Stats(maxlen=50)
