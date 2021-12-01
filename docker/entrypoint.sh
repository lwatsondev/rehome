#!/bin/sh

echo "Running database migrations..."
flask db migrate

if [ "$FLASK_ENV" = "development" ]; then
    flask run --host=0.0.0.0 --port=5000
fi
