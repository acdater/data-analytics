.PHONY: setup start stop logs init seed validate reset

setup:
	uv sync --locked

start:
	docker compose up --detach --wait

stop:
	docker compose stop

logs:
	docker compose logs --follow db

init: start
	docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' < database/schema.sql

seed: init
	uv run --env-file .env python -m northstar_retail_analytics.seed

validate:
	uv run --env-file .env python -m northstar_retail_analytics.validate

reset:
	docker compose down --volumes