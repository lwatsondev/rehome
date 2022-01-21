#!/bin/sh
gosu "$APP_USER" flask db migrate
