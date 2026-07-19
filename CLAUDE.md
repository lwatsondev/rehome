# rehome

Self-hosted Flask file upload/sharing service. Token-authenticated upload API
(`/f/`), public viewer pages (image/video/text/markdown with syntax
highlighting), expiring links, CLI for managing uploads and auth tokens.

**Stack:** Flask 3, flask-sqlalchemy-lite, Alembic migrations, Dynaconf config
(`REHOME_` env prefix), Gunicorn + Docker for prod, SQLite in WAL mode,
Sentry. npm/stylelint is used for CSS only. This is not a JS app.

## Dev workflow

- `make setup` once, then `make run` to start the app (Docker Compose, port
  5000). Never invoke Flask directly (`flask run`, `uv run flask ...`). The
  app needs the Docker environment.
- Auth token: `sqlite3 docker/data/app.db "SELECT token FROM auth_tokens LIMIT 1;"`.
  The table is `auth_tokens`. Don't rediscover this by querying `.tables`.
- `make lint` runs prek (ruff, stylelint, yamllint, hadolint, shellcheck).
- `make test` runs pytest inside Docker via the compose `test` profile.

## Releases

- Git tags are bare version numbers (`1.20.4`), never a `v` prefix.
- Version bumps update every file that declares the version and regenerate
  every lockfile that goes with it, across all package managers in the repo.
- The bump is always its own isolated commit + tag containing only those
  files, made after the commits being released, and never mixed with
  other changes.

## Python conventions

- `from module import Name`, not `import module` + `module.Name` at call
  sites, including type annotations. Import needed submodules directly with
  an alias rather than keeping the top-level package import.
- No single-character variable names anywhere, including loop and
  comprehension variables. Name caught exceptions `exc`, never `e`.
- f-strings for all interpolation, including logging calls, never %-style.
- Don't manually sort or group imports: ruff handles it. Ignore IDE
  import-sort warnings.
- Don't flag or "fix" unusual-looking syntax that already exists (e.g.
  `except A, B:`). If it runs, it's valid here.
- New source files carry the project's license header, matching the exact
  format used by existing files in the repo (SPDX or otherwise). In shell
  scripts, separate the header block from the shebang and the following code
  with a blank line on each side.
- Install dependencies with `uv sync`, update them with
  `uv sync --upgrade --all-groups`.

## Project style

- Blank lines between logical sections inside function bodies (setup,
  query, conditional, return). Don't clump everything together.
- Use `db.session.get(Model, pk)` for primary-key-only lookups, not
  `db.session.scalar(select(Model).where(...))`.
- Use `BaseModel.update(**kwargs)` (see
  [rehome/models/__init__.py](rehome/models/__init__.py)) over direct
  attribute assignment. Pass `commit=False` when the object isn't in the
  session yet, and commit after `db.session.add()`.
