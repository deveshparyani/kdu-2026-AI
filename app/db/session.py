from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# This function creates the database tables if they do not exist yet.
def init_db() -> None:
    from app.db.models import UserProfile

    Base.metadata.create_all(bind=engine)


# This function gives one database session for reading or writing data.
def get_db_session():
    return SessionLocal()
