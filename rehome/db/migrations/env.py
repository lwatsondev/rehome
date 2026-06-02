# SPDX-License-Identifier: MIT
# Copyright (c) 2021 Lee Watson

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from rehome import paths
from rehome.config import dynaconf
from rehome.models import BaseModel

db_uri = dynaconf.get("SQLALCHEMY_DATABASE_URI", f"sqlite:////{paths.DATA}/app.db")

# Provide access to the values within alembic.ini.
config = context.config

# Sets up Python logging.
fileConfig(config.config_file_name)

# Sets up metadata for autogenerate support,
config.set_main_option("sqlalchemy.url", db_uri)
target_metadata = BaseModel.metadata


def run_migrations_offline():
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine, though an
    Engine is acceptable here as well. By skipping the Engine creation we
    don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection
    with the context.
    """
    # Support injected URL for testing (see tests/conftest.py).
    if (url := config.attributes.get("sqlalchemy.url")) is not None:
        config.set_main_option("sqlalchemy.url", url)

    # If you use Alembic revision's --autogenerate flag this function will
    # prevent Alembic from creating an empty migration file if nothing changed.
    # Source: https://alembic.sqlalchemy.org/en/latest/cookbook.html
    def process_revision_directives(_, __, directives):
        if config.cmd_opts and config.cmd_opts.autogenerate:
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
