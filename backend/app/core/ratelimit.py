"""Small sliding-window rate limiter.

Counters live in memory, which is correct while the API runs as a single Railway instance.
If the API is ever scaled out, replace `_hits` with a shared store (Redis or a Postgres table);
the dependency interface below does not change.
"""

import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request

from app.core.config import settings
from app.core.security import get_current_user
from app.models import User

_hits: dict[str, deque[float]] = defaultdict(deque)


def reset_limits() -> None:
    _hits.clear()


def _check(key: str, limit: int, window: int) -> None:
    if not settings.rate_limit_enabled:
        return
    now = time.monotonic()
    hits = _hits[key]
    while hits and now - hits[0] > window:
        hits.popleft()
    if len(hits) >= limit:
        retry = max(1, int(window - (now - hits[0])))
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a moment and try again.",
            headers={"Retry-After": str(retry)},
        )
    hits.append(now)


def client_ip(request: Request) -> str:
    # Railway sits behind a proxy: the first X-Forwarded-For entry is the real client.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def limit_by_ip(limit: int, window: int, scope: str):
    def dependency(request: Request) -> None:
        _check(f"{scope}:ip:{client_ip(request)}", limit, window)

    return dependency


def limit_by_user(limit: int, window: int, scope: str):
    def dependency(user: User = Depends(get_current_user)) -> None:
        _check(f"{scope}:user:{user.id}", limit, window)

    return dependency


# Shared policies, so every route uses the same numbers.
login_limit = limit_by_ip(5, 60, "login")
signup_limit = limit_by_ip(3, 60, "signup")
default_limit = limit_by_ip(120, 60, "default")
ai_limit = limit_by_user(20, 60, "ai")
upload_limit = limit_by_user(10, 60, "upload")
studio_limit = limit_by_user(5, 60, "studio")
