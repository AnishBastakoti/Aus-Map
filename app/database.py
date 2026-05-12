from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.config import settings

engine = create_engine(
    settings.database_url,
    echo=(settings.app_env == "development"),
    pool_pre_ping=True,  # silently reconnect if the database closed the connection
)



SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,    # don't auto-send queries before you ask
    autocommit=False,   # explicit commit only — safer
    expire_on_commit=False,  # after commit, objects stay usable
)


class Base(DeclarativeBase):
    """All ORM models will inherit from this."""
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()