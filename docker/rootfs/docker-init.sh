#!/bin/sh
set -eu

cd /app || exit 1

if ! test -f "$SETTINGS_FILE_FOR_DYNACONF"; then
    echo "Copying default settings.yml"
    cp -u "$FLASK_APP/resources/config/settings.yml" "$SETTINGS_FILE_FOR_DYNACONF"
fi

flask db migrate

if test -d "$PATHS_STATIC/.webassets-cache"; then
    flask assets clean
fi

flask assets build

# shellcheck disable=SC2086
exec gunicorn "$FLASK_APP:create_app()" --worker-class gevent --bind "$GUNICORN_HOST:$GUNICORN_PORT" $GUNICORN_OPTS
