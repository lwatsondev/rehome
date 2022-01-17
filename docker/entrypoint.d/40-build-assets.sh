#!/bin/sh

echo "Updating assets"
runuser -p -u rehome -- rsync -rau /app/rehome/static/img/ "$FLASK_STATIC_DIR/img/"
runuser -p -u rehome -- flask assets clean || true
runuser -p -u rehome -- flask assets build
