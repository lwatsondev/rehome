# SPDX-License-Identifier: MIT
# Copyright (c) 2021 Lee Watson

import multiprocessing
import os

bind = os.getenv("GUNICORN_BIND", "127.0.0.1:5000")
wsgi_app = os.getenv("GUNICORN_APP", f"{os.getenv('FLASK_APP')}:create_app()")
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "gthread")
threads = os.getenv("GUNICORN_THREADS", multiprocessing.cpu_count() * 2)
workers = os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2)
timeout = os.getenv("GUNICORN_TIMEOUT", "120")
max_requests = os.getenv("GUNICORN_MAX_REQUESTS", "1000")
max_requests_jitter = os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "100")
forwarded_allow_ips = os.getenv("GUNICORN_FORWARDED_ALLOW_IPS", "*")
control_socket_disable = True
