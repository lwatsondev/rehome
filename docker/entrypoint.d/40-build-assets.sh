#!/bin/sh

echo "Updating assets"
runuser -u rehome -- rsync -rau /app/rehome/assets/img/ "$FLASK_STATIC_DIR/img/"
runuser -u rehome -- flask assets clean || true
runuser -u rehome -- flask assets build
