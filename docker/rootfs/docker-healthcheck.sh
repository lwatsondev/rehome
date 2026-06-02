#!/bin/sh
# SPDX-License-Identifier: MIT
# Copyright (c) 2021 Lee Watson
set -eu

curl -sf "http://${GUNICORN_BIND}/_/health" > /dev/null
