#!/bin/sh
set -eu

flask db migrate

if [ "${FLASK_DEBUG:-0}" = 1 ]; then
    flask run --host=0.0.0.0
fi

exec gunicorn --config /app/gunicorn.conf.py
