from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import os
import sys

# Add backend to path explicitly if needed, though alembic.ini prepend_sys_path should handle it
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import app components
from app.core.env import load_backend_env
from app.core.database import Base
# Import all models to ensure they are attached to Base.metadata
from app.domains.chat import models as chat_models
from app.domains.recommendation import models as rec_models
from app.domains.user import models as user_models # Assuming user models exist? Checking folder structure it does.

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ----------------------------------------------------------------------
# Dynamic DB URL Configuration
# ----------------------------------------------------------------------
load_backend_env()
db_url = os.getenv("DATABASE_URL")
if db_url:
    # Handle AsyncPG driver for Alembic (which is sync)
    # Usually we want sync driver for migrations? 
    # Or Alembic supports async via generic? Standard is sync.
    # If DATABASE_URL is postgresql+asyncpg://..., replace with postgresql://...
    # or let alembic handle it if configured for async (env.py needs async setup then).
    # Standard standard alembic `env.py` is sync.
    # Replacing +asyncpg with empty string to get default sync driver (psycopg2)
    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    config.set_main_option("sqlalchemy.url", sync_url)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
