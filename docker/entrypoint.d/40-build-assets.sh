#!/bin/sh
runuser -u "$APP_USER" -- rsync -rau /app/rehome/assets/img/ "$FLASK_STATIC_DIR/img/"
runuser -u "$APP_USER" -- flask assets clean || true
runuser -u "$APP_USER" -- flask assets build
