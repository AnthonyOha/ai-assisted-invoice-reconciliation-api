# app/graphql/context.py
from dataclasses import dataclass
from sqlalchemy.orm import Session

@dataclass
class Context:
    db: Session
