#!/bin/sh
set -eu

curl -sf "http://${GUNICORN_BIND}/_/health" > /dev/null
