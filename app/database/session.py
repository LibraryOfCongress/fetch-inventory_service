from sqlmodel import create_engine, Session
from fastapi import Request

from contextlib import contextmanager
from app.config.config import get_settings

engine = create_engine(
    get_settings().DATABASE_URL, echo=get_settings().ENABLE_ORM_SQL_LOGGING
)


def get_session(request: Request = None):
    """
    Database sessions are injected as Path Operation Dependencies
    """
    with Session(engine) as session:
        existing_session = None if not request else getattr(request.state, 'db_session', None)
        yield session if not existing_session else existing_session


@contextmanager
def session_manager():
    """
    For use when a generator is not valid
    """
    session = next(get_session())
    try:
        yield session
    finally:
        session.close()


def commit_record(session, record):
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def bulk_commit_records(session, records):
    session.bulk_save_objects(records)
    session.commit()
    session.refresh(records)
    return records


def remove_record(session, record):
    session.delete(record)
    session.commit()
