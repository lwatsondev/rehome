#!/bin/sh

echo "Starting app"
exec runuser -u rehome -- "$@"
