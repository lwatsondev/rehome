#!/bin/sh
# SPDX-License-Identifier: MIT
# Copyright (c) 2021 Lee Watson
set -eu

flask db migrate

if [ "${FLASK_DEBUG:-0}" = 1 ]; then
    flask run --host=0.0.0.0 \
        --extra-files "/app/rehome/resources/config/default.toml:${ROOT_PATH_FOR_DYNACONF:-/config}"
fi

exec gunicorn --config /app/gunicorn.conf.py
