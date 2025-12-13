#!/bin/sh
set -eu

flask db migrate

if [ "${FLASK_DEBUG:-0}" = 1 ]; then
    flask run --host=0.0.0.0
fi

# shellcheck disable=SC2086
exec gunicorn "${FLASK_APP}:create_app()" --bind "${GUNICORN_HOST}:${GUNICORN_PORT}" ${GUNICORN_OPTS:-}
