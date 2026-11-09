PROFILE ?= development
BATCH_SIZE ?= 5000
.PHONY: setup start stop logs init seed validate test test-integration reset
setup:
	uv sync --locked
start:
	docker compose up --detach --wait
stop:
	docker compose stop
logs:
	docker compose logs --follow db
init: start
	uv run --locked --env-file .env arcadia init
seed: init
	uv run --locked --env-file .env arcadia generate --profile $(PROFILE) --batch-size $(BATCH_SIZE)
validate:
	uv run --locked --env-file .env arcadia validate
test:
	uv run --locked pytest -m 'not integration'
test-integration:
	ARCADIA_TEST_DATABASE=1 uv run --locked --env-file .env pytest -m integration
reset:
	docker compose down --volumes
