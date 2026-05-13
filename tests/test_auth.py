from http import HTTPStatus

import pytest
from sqlalchemy import select

from rehome import auth, create_app
from rehome.extensions import db
from rehome.models import BaseModel
from rehome.models.auth_token import AuthToken


@pytest.fixture
def bare_app():
    app = create_app(
        test_config={
            "TESTING": True,
            "SECRET_KEY": "test",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )
    with app.app_context():
        BaseModel.metadata.create_all(db.engine)
        yield app
        BaseModel.metadata.drop_all(db.engine)


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


def test_ensure_auth_token_creates_default(bare_app):
    auth.ensure_auth_token(bare_app)

    with bare_app.app_context():
        tokens = db.session.scalars(select(AuthToken)).all()

    assert len(tokens) == 1
    assert tokens[0].name == "default"


def test_ensure_auth_token_is_idempotent(bare_app):
    auth.ensure_auth_token(bare_app)
    auth.ensure_auth_token(bare_app)

    with bare_app.app_context():
        tokens = db.session.scalars(select(AuthToken)).all()

    assert len(tokens) == 1
