.PHONY: setup run test

TTY_FLAG := $(shell [ -t 0 ] || echo "-T")

setup:
	uv sync
	yarn install
	uv run pre-commit install

run:
	docker compose -f docker/compose.yaml up --build

test:
	docker compose -f docker/compose.yaml --profile test run --rm $(TTY_FLAG) --build test
