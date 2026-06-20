# SPDX-License-Identifier: MIT
# Copyright (c) 2021 Lee Watson

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from rehome.extensions import db
from rehome.models.upload import Upload

if TYPE_CHECKING:
    from flask import Flask


def start(app: Flask):
    scheduler = BackgroundScheduler()
    interval = app.config.get("uploads.expired_cleanup_interval_hours", 24)
    scheduler.add_job(
        lambda: _purge_expired_uploads(app),
        IntervalTrigger(hours=interval),
        next_run_time=datetime.now(UTC),  # Run immediately on startup.
    )
    app.logger.debug("Starting expired upload cleanup task.")
    scheduler.start()


def _purge_expired_uploads(app: Flask):
    with app.app_context():
        # create_app() may be called before the database is initialized such as during migration.
        try:
            expired = db.session.scalars(select(Upload).where(Upload.is_expired)).all()
        except OperationalError:
            return

        for upload in expired:
            upload.delete(commit=False)

        if expired:
            db.session.commit()
            app.logger.info(f"Purged {len(expired)} expired upload(s).")
