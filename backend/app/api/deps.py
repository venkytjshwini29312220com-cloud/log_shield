from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.session import get_db as db_session


def settings_dep(settings: Settings = Depends(get_settings)) -> Settings:
    return settings


def get_db() -> Generator[Session, None, None]:
    yield from db_session()
