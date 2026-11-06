from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base, Bundle, Network


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    with TestingSession() as db:
        for network_id, name, short_name in (
            ("mtn", "MTN", "MTN"),
            ("telecel", "Telecel", "Telecel"),
            ("at", "AirtelTigo", "AT"),
        ):
            db.add(Network(id=network_id, name=name, short_name=short_name))
            db.add(
                Bundle(
                    id=f"{network_id}-sample-1gb",
                    network_id=network_id,
                    name="1 GB sample bundle",
                    size_gb=1,
                    amount=1,
                    currency="GHS",
                    is_sample=True,
                    is_available=True,
                )
            )
        db.commit()

    def override_get_db() -> Generator[Session, None, None]:
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()
