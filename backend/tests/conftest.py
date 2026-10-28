import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite:///./test_smartbook.db"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["DEFAULT_RENTAL_DAYS"] = "14"
os.environ["MAX_ACTIVE_RENTALS"] = "2"

from fastapi.testclient import TestClient
import pytest

from app.database import Base, engine
from app.main import app


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)
    Path("test_smartbook.db").unlink(missing_ok=True)