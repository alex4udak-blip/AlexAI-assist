"""Alembic environment configuration."""

import asyncio
import logging
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from src.core.config import settings
from src.db.base import Base
from src.db.models import *  # noqa: F401, F403

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("alembic.env")

config = context.config
config.set_main_option("sqlalchemy.url", settings.async_database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    logger.info("Connecting to database for migrations...")

    # Add connection timeout
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={
            "timeout": 30,  # 30 second connection timeout
            "command_timeout": 60,  # 60 second query timeout
        },
    )

    try:
        async with connectable.connect() as connection:
            logger.info("Database connected, running migrations...")
            await connection.run_sync(do_run_migrations)
            logger.info("Migrations completed successfully")
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    try:
        asyncio.run(run_async_migrations())
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
