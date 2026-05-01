"""
Alembic migration environment.
Configured for async SQLAlchemy with autogenerate support.
"""

from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

from app.config import get_settings
from app.db.base import Base
import app.db.models  # noqa: F401 — registers all models for autogenerate

cfg_alembic = context.config
cfg_app = get_settings()

if cfg_alembic.config_file_name is not None:
    fileConfig(cfg_alembic.config_file_name)

target_metadata = Base.metadata


def run_migrations_online():
    """Run migrations in online mode using async engine."""
    connectable = create_async_engine(
        cfg_app.database_url.replace("postgresql://", "postgresql+asyncpg://"),
        poolclass=pool.NullPool,
    )

    import asyncio

    async def do_run():
        async with connectable.connect() as connection:
            await connection.run_sync(context.configure, connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                await connection.run_sync(context.run_migrations)

    asyncio.run(do_run())


run_migrations_online()
