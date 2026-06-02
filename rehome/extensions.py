# SPDX-License-Identifier: MIT
# Copyright (c) 2021 Lee Watson

from importlib.util import find_spec

from dynaconf import FlaskDynaconf
from flask_sqlalchemy_lite import SQLAlchemy

from rehome.config import dynaconf

dynaconf = FlaskDynaconf(dynaconf_instance=dynaconf)
db = SQLAlchemy()
debugbar = None

if find_spec("flask_debugtoolbar"):
    from flask_debugtoolbar import DebugToolbarExtension

    debugbar = DebugToolbarExtension()
