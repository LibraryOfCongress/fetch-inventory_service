import pytz, os

from logging.config import fileConfig
from datetime import datetime

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlmodel import SQLModel

from alembic import context

from app.config.config import get_settings


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Check for an environment variable
use_migration_url = os.getenv('USE_MIGRATION_URL', 'False').lower() == 'true'

# Set the database URL based on the environment variable
if use_migration_url:
    # migrations external from container
    config.set_main_option("sqlalchemy.url", get_settings().MIGRATION_URL)
else:
    # ORM url within running container
    config.set_main_option("sqlalchemy.url", get_settings().DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from migrations.models import *

# target_metadata = mymodel.Base.metadata
target_metadata = SQLModel.metadata

# Filter out raw sql tables
def include_object(object, name, type_, reflected, compare_to):
    # remove this from filtering after we change to class based approach
    if type_ == "table" and name == "audit_log":
        return False
    return True

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
        include_object=include_object,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    def process_revision_directives(context, revision, directives):
        """
        Labels migration file autogeneration by inverted date
        # 20230801211024 for a migration generated on Aug 1st, 2023 at 21:10:24
        """
        eastern = pytz.timezone('US/Eastern')
        current_time_et = datetime.now(eastern)
        rev_id = current_time_et.strftime("%Y_%m_%d_%H:%M:%S")
        for directive in directives:
            directive.rev_id = rev_id

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            process_revision_directives=process_revision_directives
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
