.PHONY: help install up down test seed pipeline backend frontend clean

help:
	@echo "MARINeX SIH26143 Developer Commands:"
	@echo "  make install    - Install Python backend dependencies"
	@echo "  make test       - Run backend unit and integration tests"
	@echo "  make seed       - Seed database with Mumbai Offshore demo scenario"
	@echo "  make pipeline   - Run full end-to-end pipeline via CLI"
	@echo "  make backend    - Start local FastAPI backend (port 8000)"
	@echo "  make frontend   - Start local Vite React frontend (port 5173)"
	@echo "  make up         - Start all containers via docker-compose"
	@echo "  make down       - Stop all containers"
	@echo "  make clean      - Clean temporary files and caches"

install:
	pip install -r backend/requirements.txt

test:
	python -m pytest backend/tests -v

seed:
	python scripts/seed_demo_data.py

pipeline:
	python scripts/run_pipeline_cli.py

backend:
	uvicorn app.main:app --app-dir backend --reload --port 8000

frontend:
	cd frontend && npm run dev

up:
	docker compose up --build -d

down:
	docker compose down

clean:
	rm -rf .pytest_cache **/__pycache__ backend/test_marinex.db
