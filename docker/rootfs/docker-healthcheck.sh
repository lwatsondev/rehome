#!/bin/sh
set -eu

curl -sf "http://${GUNICORN_HOST}:${GUNICORN_PORT}/_/health" > /dev/null
