#!/bin/sh

echo "Running database migrations"
runuser -u rehome -- flask db migrate
