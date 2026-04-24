import pytest

from rehome import create_app
from rehome.extensions import db
from rehome.models import BaseModel

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
    app.config["auth.token"] = AUTH_TOKEN
    with app.app_context():
        BaseModel.metadata.create_all(db.engine)
        yield app
        BaseModel.metadata.drop_all(db.engine)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {AUTH_TOKEN}"}
