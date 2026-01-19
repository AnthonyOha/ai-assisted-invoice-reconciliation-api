from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


def create_db_engine(database_url: str | None = None):
    url = database_url or settings.database_url
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(url, echo=False, future=True, connect_args=connect_args)


ENGINE = create_db_engine()
SessionLocal = sessionmaker(bind=ENGINE, class_=Session, expire_on_commit=False, autoflush=False)


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
