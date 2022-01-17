#!/bin/sh

if test -z "$PUID" && test -z "$PGID"; then
    echo "Neither PUID or PGID are set, skipping permission fixes."
    exit 0
fi

if test -n "$PUID"; then
    echo "Changing UID of rehome to $PUID"
    usermod -u "$PUID" rehome
fi

if test -n "$PGID"; then
    echo "Changing GID of rehome to $PGID"
    groupmod -g "$PGID" rehome
fi

echo "Changing ownership of app files"
chown -R rehome:rehome /config /data /app /static
