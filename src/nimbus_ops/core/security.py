from __future__ import annotations

import hmac


def token_matches(provided: str | None, expected: str) -> bool:
    if provided is None:
        return False
    normalized = provided.replace("Bearer ", "", 1).strip()
    return hmac.compare_digest(normalized, expected)
