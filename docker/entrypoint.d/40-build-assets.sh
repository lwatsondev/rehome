#!/bin/sh
runuser -u "$APP_USER" -- rsync -rauq /app/rehome/assets/img/ "$PATHS_STATIC/img/"
runuser -u "$APP_USER" -- flask assets clean || true
runuser -u "$APP_USER" -- flask assets build
