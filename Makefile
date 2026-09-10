.PHONY: help install install-ml up down test test-ml seed pipeline backend frontend download-sample data-status audit data-verify prepare-ais explain clean

help:
	@echo "MARINeX SIH26143 Developer Commands:"
	@echo "  make install           - Install Python backend dependencies (backend/requirements.txt)"
	@echo "  make install-ml        - Install ML/data deps into .venv (ml/requirements.txt)"
	@echo "  make test              - Run backend unit and integration tests (backend/tests)"
	@echo "  make test-ml           - Run ML/data layer tests (ml/tests)"
	@echo "  make seed              - Seed database with Mumbai Offshore demo scenario"
	@echo "  make pipeline          - Run full end-to-end pipeline via CLI"
	@echo "  make backend           - Start local FastAPI backend (port 8000)"
	@echo "  make frontend          - Start local Vite React frontend (port 5173)"
	@echo "  make up                - Start all containers via docker-compose"
	@echo "  make down              - Stop all containers"
	@echo "  make download-sample   - Refresh manifests + validate sample datasets (no external fetch)"
	@echo "  make data-status       - Show manifest catalog table (scripts/data_status.py)"
	@echo "  make audit             - Run SAR dataset audit (leakage/checksums) -> reports/sar_dataset_report.md"
	@echo "  make prepare-ais       - Prepare sample AIS CSV -> partitioned parquet (scripts/prepare_ais.py)"
	@echo "  make explain           - Generate explainability panel for a patch (ml/explain.py)"
	@echo "  make clean             - Clean temporary files and caches"

install:
	pip install -r backend/requirements.txt

install-ml:
	.venv\Scripts\python -m pip install -r ml/requirements.txt

test:
	python -m pytest backend/tests -v

test-ml:
	.venv\Scripts\python -m pytest ml/tests -v

seed:
	python scripts/seed_demo_data.py

pipeline:
	python scripts/run_pipeline_cli.py

download-sample:
	.venv\Scripts\python -m ml.data_audit.audit_dataset --datasets p

data-status:
	.venv\Scripts\python scripts/data_status.py

audit:
	.venv\Scripts\python -m ml.data_audit.audit_dataset --datasets p,e

prepare-ais:
	.venv\Scripts\python scripts/prepare_ais.py --input data/samples/sample_ais_trajectories.csv --output data/processed/ais/partitions --region 71.0 71.7 19.0 19.6 --start 2026-03-01T00:00:00Z --end 2026-03-02T00:00:00Z

explain:
	.venv\Scripts\python ml/explain.py --checkpoint models/checkpoints/segformer_primary_best.pt --model segformer --image data/datasets/sentinel1_primary/images/patch_0101.png --mask data/datasets/sentinel1_primary/masks/patch_0101.png --methods occlusion,gradcam,attention --out reports/explainability/patch_0101_panel.png

up:
	docker compose up --build -d

down:
	docker compose down

clean:
	rm -rf .pytest_cache **/__pycache__ backend/test_marinex.db
