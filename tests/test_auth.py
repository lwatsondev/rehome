from http import HTTPStatus

import pytest

from rehome import create_app
from rehome.extensions import db
from rehome.models import BaseModel


@pytest.fixture
def no_tokens_client():
    app = create_app(
        test_config={
            "TESTING": True,
            "SECRET_KEY": "test",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )
    with app.app_context():
        BaseModel.metadata.create_all(db.engine)
        yield app.test_client()
        BaseModel.metadata.drop_all(db.engine)


def test_no_credentials(no_tokens_client):
    response = no_tokens_client.post("/f/")
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_empty_bearer(no_tokens_client):
    response = no_tokens_client.post("/f/", headers={"Authorization": "Bearer "})
    assert response.status_code == HTTPStatus.UNAUTHORIZED
