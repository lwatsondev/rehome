#!/bin/sh
runuser -u "$APP_USER" -- mkdir "$FLASK_STATIC_DIR/img/" > /dev/null 2>&1 || true
runuser -u "$APP_USER" -- cp -rau /app/rehome/assets/img/* "$FLASK_STATIC_DIR/img/"
runuser -u "$APP_USER" -- flask assets clean || true
runuser -u "$APP_USER" -- flask assets build
