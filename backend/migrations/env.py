"""Alembic environment for the backend catalog schema."""

from logging.config import fileConfig
import os

from alembic import context
from backend.app.database import get_database_url
from backend.app.database import create_database_engine
from backend.app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = (
    os.environ.get("DATABASE_URL")
    or config.get_main_option("sqlalchemy.url")
    or get_database_url()
)
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating an Engine."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a database connection."""
    connectable = create_database_engine(config.get_main_option("sqlalchemy.url"))
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
