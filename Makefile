.PHONY: help up down build logs logs-api shell-api shell-db test clean

help:
	@echo ""
	@echo "  DocuMind — Commands"
	@echo "  ───────────────────────────────────"
	@echo "  make up         Start all services"
	@echo "  make down       Stop all services"
	@echo "  make build      Rebuild images"
	@echo "  make logs       Tail all logs"
	@echo "  make logs-api   Tail backend logs"
	@echo "  make shell-api  Shell into backend"
	@echo "  make shell-db   psql into Postgres"
	@echo "  make test       Run backend tests"
	@echo "  make clean      Remove volumes + containers"
	@echo ""

up:
	docker compose up -d

up-watch:
	docker compose up

down:
	docker compose down

build:
	docker compose build --no-cache

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f backend

logs-fe:
	docker compose logs -f frontend

shell-api:
	docker compose exec backend bash

shell-db:
	docker compose exec db psql -U documind -d documind

test:
	docker compose exec backend pytest tests/ -v

clean:
	docker compose down -v --remove-orphans
	docker system prune -f

restart-backend:
	docker compose restart backend
