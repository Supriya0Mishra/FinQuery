"""API tests run against in-memory SQLite and fake storage/queue, so they need
no Docker services."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.invoices import get_enqueue
from app.db.session import Base, get_db
from app.main import app
from app.services.storage import get_storage


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data

    def get(self, key: str) -> bytes:
        return self.objects[key]


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def storage() -> FakeStorage:
    return FakeStorage()


@pytest.fixture
def enqueued() -> list:
    return []


@pytest.fixture
def client(session_factory, storage, enqueued):
    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_enqueue] = lambda: enqueued.append
    # No `with`: skips the lifespan hook, which would try to reach real S3.
    yield TestClient(app)
    app.dependency_overrides.clear()
