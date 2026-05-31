from __future__ import annotations

from app.modules.flow_controller.persistence_adapter import list_leaderboard


def get_leaderboard(*, limit: int = 50) -> list[dict[str, str | int]]:
    safe_limit = max(1, min(int(limit), 100))
    rows = list_leaderboard(limit=safe_limit)
    return [
        {
            "rank": idx,
            **row,
        }
        for idx, row in enumerate(rows, start=1)
    ]
