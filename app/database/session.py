# --- UPDATED IMPORTS ---
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker # Use standard SQLAlchemy Session
from fastapi import Request

from contextlib import contextmanager
from typing import Generator
# Assuming get_settings is still imported correctly
from app.config.config import get_settings


# --- ENGINE DEFINITIONS ---

# The engine for the main application (used for AppSessionLocal and get_session)
engine = create_engine(
    get_settings().DATABASE_URL,
    echo=get_settings().ENABLE_ORM_SQL_LOGGING,
    future=True,
    pool_pre_ping=True,
    pool_recycle=1800,
)

# The engine for data migration (used for sa_hybrid_session_local)
data_migration_engine = create_engine(
    get_settings().DATABASE_URL,
    echo=get_settings().ENABLE_ORM_SQL_LOGGING,
    pool_size=20,       # Increase the pool size
    max_overflow=20,    # Allow more overflow connections if needed
    pool_timeout=30,    # Timeout before raising an exception if no connections are available
    future=True
)

# --- SESSION FACTORIES ---

# Factory for data migration engine
sa_hybrid_session_local = sessionmaker(autocommit=False, autoflush=False, bind=data_migration_engine, class_=Session)

# New session factory specifically for the main application engine.
AppSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)


# --- DEPENDENCY INJECTION / GENERATOR FUNCTION ---
# Note: Since you are using synchronous connections, this is a standard generator.
def get_session(request: Request = None) -> Generator[Session, None, None]:
    with Session(engine, autoflush=False) as session: # Session is now from sqlalchemy.orm
        with session.no_autoflush:
            # Transfer audit_info from middleware session to this DI session
            if request and hasattr(request, 'state') and hasattr(request.state, 'db_session'):
                middleware_session = request.state.db_session
                audit_info = getattr(middleware_session, "audit_info", None)
                if audit_info:
                    setattr(session, "audit_info", audit_info)
                    from app.utilities import start_session_with_audit_info
                    start_session_with_audit_info(audit_info, session)
            try:
                yield session
            except Exception:
                session.rollback()
                raise

# --- OTHER UTILITY FUNCTIONS (UPDATES ONLY WHERE NEEDED) ---

def get_sqlalchemy_session():
    """
    Hybrid session that allows SQLAlchemy to register
    SQLModel base classes. This is used in data seeding
    to harness lower level power of SQLAlchemy without
    us having to do a refactor.
    """
    # NOTE: The description here will be outdated, as SQLModel is being removed.
    # The actual code remains unchanged as it uses the factory.
    db = sa_hybrid_session_local()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def session_manager():
    """
    For use when a generator is not valid
    Context manager for database sessions.
    Ensures sessions are properly scoped and closed.
    """
    # Session is now from sqlalchemy.orm
    session = Session(engine, autoflush=False)  # Disabling autoflush to prevent unintended mutations
    try:
        yield session
        # our commits are called explicitly on purpose
        # session.commit()  # Commit only if everything is successful
    except Exception:
        session.rollback()  # Rollback in case of error
        raise
    finally:
        session.close()  # Always close the session


def commit_record(session, record):
    audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"})
    session.add(record)
    session.commit()
    session.refresh(record)
    from app.utilities import start_session_with_audit_info
    start_session_with_audit_info(audit_info, session)
    return record


def bulk_commit_records(session, records):
    audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"})
    session.bulk_save_objects(records)
    session.commit()
    # session.refresh(records) # session.refresh() does not work on a list
    from app.utilities import start_session_with_audit_info
    start_session_with_audit_info(audit_info, session)
    return records


def remove_record(session, record):
    session.delete(record)
    session.commit()
