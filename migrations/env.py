# /migrations/env.py - ULTIMATE FIX FOR NoReferencedTableError

import os
import importlib # <-- NEW IMPORT
import pkgutil # <-- NEW IMPORT

from logging.config import fileConfig
from datetime import datetime, timezone

from sqlalchemy import engine_from_config
from sqlalchemy import pool
# REMOVED: from sqlmodel import SQLModel
# ADDED: Import the new Base class from your corrected location
from app.database.base import Base # <--- CRITICAL CHANGE

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


# =======================================================================
# CRITICAL FIX: Programmatic model discovery to ensure ALL models are loaded
# =======================================================================
def import_all_models():
    """Dynamically imports all modules under the app.models package."""
    
    # We must ensure app.models is imported first to get its path (__path__)
    models_package = importlib.import_module('app.models')

    # Recursively walk the package to find and import every module.
    for module_loader, name, is_pkg in pkgutil.walk_packages(
        models_package.__path__,
        models_package.__name__ + '.'
    ):
        try:
            importlib.import_module(name)
        except Exception as e:
            # Optionally log which model file failed to load, but typically all should load cleanly now.
            print(f"Warning: Failed to import model {name}: {e}")
            pass

# --- EXECUTE THE SCAN HERE ---
import_all_models()
# --- END EXECUTE THE SCAN ---


# target_metadata = mymodel.Base.metadata
# CRITICAL CHANGE: Use Base.metadata instead of SQLModel.metadata
target_metadata = Base.metadata


# Filter out raw sql tables
def include_object(object, name, type_, reflected, compare_to):
    # This filter can be simplified after all models inherit from Base
    # but for now, keep the audit_log exclusion
    if type_ == "table" and name == "audit_log":
        return False
    return True

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
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
    """Run migrations in 'online' mode."""
    def process_revision_directives(context, revision, directives):
        """
        Labels migration file autogeneration by inverted date
        """
        # eastern = pytz.timezone('US/Eastern')
        # current_time_et = datetime.now(eastern)
        current_time_utc = datetime.now(timezone.utc)
        # We already fixed this to use underscores in the previous step
        rev_id = current_time_utc.strftime("%Y_%m_%d_%H_%M_%S")
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
            process_revision_directives=process_revision_directives,
            transaction_per_migration=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()