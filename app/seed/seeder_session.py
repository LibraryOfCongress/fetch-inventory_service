from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.config import get_settings

# Create the SQLAlchemy engine
engine = create_engine(
    get_settings().DATABASE_URL,
    echo=get_settings().ENABLE_ORM_SQL_LOGGING
)

# Create a sessionmaker bound to the engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session():
    """
    Unlike ORM db session which returns a generator, this returns
    a Session class instance to fill Seeder's needs.
    """
    return SessionLocal()
