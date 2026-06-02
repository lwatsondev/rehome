# SPDX-License-Identifier: MIT
# Copyright (c) 2021 Lee Watson

from http import HTTPStatus


def test_index(client):
    response = client.get("/")
    assert response.status_code == HTTPStatus.OK
