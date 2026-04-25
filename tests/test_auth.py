from http import HTTPStatus

import pytest

from rehome import create_app
from rehome.extensions import db
from rehome.models import BaseModel


@pytest.fixture
def empty_token_client():
    app = create_app(
        test_config={
            "TESTING": True,
            "SECRET_KEY": "test",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )
    app.config["auth.token"] = ""
    with app.app_context():
        BaseModel.metadata.create_all(db.engine)
        yield app.test_client()
        BaseModel.metadata.drop_all(db.engine)


def test_empty_token_no_credentials(empty_token_client):
    response = empty_token_client.post("/f/")
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_empty_token_empty_bearer(empty_token_client):
    response = empty_token_client.post("/f/", headers={"Authorization": "Bearer "})
    assert response.status_code == HTTPStatus.UNAUTHORIZED
