from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database.session import reset_engine
from app.main import create_app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "logshield-test.db"
    monkeypatch.setenv("LOGSHIELD_DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    get_settings.cache_clear()
    reset_engine()
    application = create_app()
    with TestClient(application) as test_client:
        yield test_client
    reset_engine()
    get_settings.cache_clear()
