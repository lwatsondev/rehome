#!/bin/sh
set -eu

if [ "${FLASK_DEBUG:-0}" = 1 ]; then
    flask run --host=0.0.0.0
fi

# shellcheck disable=SC2086
exec gunicorn "${FLASK_APP}:create_app()" --worker-class gevent --bind "${GUNICORN_HOST}:${GUNICORN_PORT}" ${GUNICORN_OPTS:-}
