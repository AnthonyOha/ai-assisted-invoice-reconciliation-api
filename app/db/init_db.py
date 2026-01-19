from __future__ import annotations

from app.db.base import Base
from app.db.session import ENGINE
from app.models import models  # noqa: F401  (ensure models are imported)


def init_db() -> None:
    Base.metadata.create_all(bind=ENGINE)
