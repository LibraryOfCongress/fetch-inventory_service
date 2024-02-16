from sqlmodel import create_engine, Session

from app.config.config import get_settings


engine = create_engine(
    get_settings().DATABASE_URL, echo=get_settings().ENABLE_ORM_SQL_LOGGING
)


def get_session():
    """
    Database sessions are injected as Path Operation Dependencies
    """
    with Session(engine) as session:
        yield session


def commit_record(session, record):
    session.add(record)
    session.commit()
    session.refresh(record)
    return record
