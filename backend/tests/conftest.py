from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base, Bundle, Network, Permission, Role, RolePermission
from app.services.admin_security import DEFAULT_ROLE_PERMISSION_GRANTS


@pytest.fixture
def db_session_factory() -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    with TestingSession() as db:
        permission_codes = {
            permission
            for permissions in DEFAULT_ROLE_PERMISSION_GRANTS.values()
            for permission in permissions
        }
        for role_name in DEFAULT_ROLE_PERMISSION_GRANTS:
            db.add(
                Role(
                    name=role_name,
                    display_name=role_name.replace("_", " ").title(),
                    description=f"{role_name.replace('_', ' ').title()} access",
                )
            )
        for permission_code in permission_codes:
            db.add(
                Permission(
                    code=permission_code,
                    description=permission_code.replace(".", " ").replace("_", " ").title(),
                )
            )
        db.flush()
        for role_name, permissions in DEFAULT_ROLE_PERMISSION_GRANTS.items():
            db.add_all(
                RolePermission(role_name=role_name, permission_code=permission)
                for permission in permissions
            )
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
    yield TestingSession
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(
    db_session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        with db_session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
