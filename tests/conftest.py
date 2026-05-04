import pytest
from alembic.config import Config as AlembicConfig

import rehome.paths
from rehome import create_app
from rehome.extensions import db
from rehome.models import BaseModel
from rehome.models.auth_token import AuthToken

AUTH_TOKEN = "test-token"


@pytest.fixture
def app():
    app = create_app(
        test_config={
            "TESTING": True,
            "SECRET_KEY": "test",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        }
    )
    with app.app_context():
        BaseModel.metadata.create_all(db.engine)
        token = AuthToken.generate("test")
        token.update(token=AUTH_TOKEN, commit=False)
        db.session.add(token)
        db.session.commit()
        yield app
        BaseModel.metadata.drop_all(db.engine)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {AUTH_TOKEN}"}


@pytest.fixture
def migration_db_url(tmp_path):
    return f"sqlite:///{tmp_path / 'migrations.db'}"


@pytest.fixture
def alembic_cfg(migration_db_url, monkeypatch):
    monkeypatch.setattr(
        rehome.paths, "ensure_dirs", lambda: None
    )  # Prevent creating instance/data directories during migration tests.

    cfg = AlembicConfig("alembic.ini")
    cfg.attributes["sqlalchemy.url"] = migration_db_url
    return cfg
