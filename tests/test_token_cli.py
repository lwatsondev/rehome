from http import HTTPStatus

from rehome.extensions import db
from rehome.models.auth_token import AuthToken


def test_created_token_authenticates(app, client):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["token", "create", "new"])
    token = result.output.strip()
    response = client.post("/f/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code != HTTPStatus.UNAUTHORIZED


def test_create_duplicate_name_fails(app):
    runner = app.test_cli_runner()
    runner.invoke(args=["token", "create", "dup"])
    result = runner.invoke(args=["token", "create", "dup"])
    assert result.exit_code != 0


def test_deleted_token_no_longer_authenticates(app, client):
    runner = app.test_cli_runner()
    create_result = runner.invoke(args=["token", "create", "temp"])
    token = create_result.output.strip()
    runner.invoke(args=["token", "delete", "temp"])
    response = client.post("/f/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_delete_nonexistent_fails(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["token", "delete", "ghost"])
    assert result.exit_code != 0


def test_last_used_updated_on_auth(app, client, auth_headers):
    with app.app_context():
        token = db.session.get(AuthToken, "test")
        assert token.last_used_at is None

    client.post("/f/", headers=auth_headers)

    with app.app_context():
        token = db.session.get(AuthToken, "test")
        assert token.last_used_at is not None
