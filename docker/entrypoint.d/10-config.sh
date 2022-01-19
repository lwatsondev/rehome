#!/bin/sh

if [ ! -f "$SETTINGS_FILE_FOR_DYNACONF" ]; then
    echo "Copying default settings.yml"
    rsync -auq /app/rehome/resources/config/settings.yml "$SETTINGS_FILE_FOR_DYNACONF"
fi
