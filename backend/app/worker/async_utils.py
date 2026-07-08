"""
Shared helper for running the async body of a Celery task.

Every Celery task entrypoint in this project is a sync function that does
`asyncio.run(_the_actual_async_task())`. `asyncio.run()` creates a brand-new
event loop for the duration of that single call and tears it down when the
call returns.

`app.db.session.engine` (a SQLAlchemy `AsyncEngine` wrapping an asyncpg
connection pool) is a process-wide singleton, imported both by the FastAPI
`api` process and by every `worker`/`beat` process. FastAPI keeps one event
loop alive for the life of the process, so pooling behaves normally there.
Celery's prefork workers, however, are long-lived processes that execute
many tasks back-to-back over their lifetime — each via its own
`asyncio.run()` call, i.e. its own event loop.

Without this helper, a connection checked out and returned to the pool
during task #1's loop is still sitting in the pool when task #2 starts a
*new* loop. asyncpg connections are bound to the loop that created them, so
reusing one under a different loop raises `RuntimeError: Event loop is
closed` or "... attached to a different loop" (this is not hypothetical —
it was observed in production logs from `check_grace_periods`). Because the
failure happens inside SQLAlchemy's connection checkout/pre-ping, it can
break unrelated tasks running later in the same worker process, well after
whatever first triggered it.

`run_async_task` disposes the engine's pool at the end of every task body,
while its own loop is still running, so the pool starts empty for the next
`asyncio.run()` call and lazily opens fresh connections under that loop.
This trades a small amount of reconnect overhead (these are hourly/12h
periodic tasks, not a hot path) for correctness.
"""

from typing import Coroutine, TypeVar

from app.db.session import engine

T = TypeVar("T")


async def run_async_task(coro: Coroutine[None, None, T]) -> T:
    try:
        return await coro
    finally:
        await engine.dispose()
