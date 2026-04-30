.PHONY: help install acquire acquire-njgin acquire-dlgs acquire-sr1a ingest ingest-njgin extract-dlgs ingest-sr1a reconcile validate all clean test build-geojson build-renovations build-cohort-history build-parcels-full viz-data viz-install viz-dev

PYTHON := uv run python
TODAY := $(shell date +%Y-%m-%d)

help:
	@echo "fairhaven_tax pipeline targets:"
	@echo "  make install         - uv sync (install deps)"
	@echo "  make acquire         - download all three raw datasets to data/raw/<source>/$(TODAY)/"
	@echo "  make acquire-njgin   - download Monmouth Parcels+MOD-IV FGDB only"
	@echo "  make acquire-dlgs    - download DLGS Property Tax Tables only"
	@echo "  make acquire-sr1a    - download SR1A 2018-2025 only"
	@echo "  make ingest          - parse raw -> data/processed/ parquet"
	@echo "  make ingest-njgin    - NJGIN -> parcels.parquet"
	@echo "  make extract-dlgs    - DLGS xlsx -> populate constants.py"
	@echo "  make ingest-sr1a     - SR1A -> sales.parquet + rejections.parquet"
	@echo "  make reconcile       - MOD-IV ↔ SR1A last-sale reconciliation"
	@echo "  make validate        - run validation gate (D-09)"
	@echo "  make all             - acquire + ingest + validate"
	@echo "  make test            - pytest"
	@echo "  make clean           - rm -rf data/processed/ (raw is preserved)"

install:
	uv sync

acquire: acquire-njgin acquire-dlgs acquire-sr1a

acquire-njgin:
	$(PYTHON) scripts/acquire_njgin.py

acquire-dlgs:
	$(PYTHON) scripts/acquire_dlgs.py

acquire-sr1a:
	$(PYTHON) scripts/acquire_sr1a.py

ingest-njgin:
	$(PYTHON) scripts/ingest_njgin.py

extract-dlgs:
	$(PYTHON) scripts/extract_dlgs.py

ingest-sr1a:
	$(PYTHON) scripts/ingest_sr1a.py

reconcile:
	$(PYTHON) scripts/reconcile.py

ingest: ingest-njgin extract-dlgs ingest-sr1a reconcile

validate:
	$(PYTHON) scripts/validate_phase1.py

all: acquire ingest validate

test:
	uv run pytest -q

clean:
	rm -rf data/processed/

# Phase 2 viz targets
build-geojson:
	$(PYTHON) scripts/build_parcels_geojson.py

# Renovation derivation: triangulates 3 signals (improvement-value step-up
# w/ MAD residualization, eff_age compression, building-description change).
# Outputs renovation_events.parquet, renovation_summary.parquet, and the
# viz overlay JSON. Reproducible from data/processed/* — no manual steps.
build-renovations:
	$(PYTHON) scripts/derive_renovation_events.py

# Cohort time-series: per-cohort annual avg assessed value, share of total,
# tax-bill trajectory. Powers the cumulative-undertaxation view on
# /town-composition.
build-cohort-history:
	$(PYTHON) scripts/build_cohort_history.py

# Aggregator: combines all per-parcel sources into viz/src/data/parcels_full.json
# and viz/src/data/town_aggregates.json. Depends on renovations overlay.
build-parcels-full: build-renovations
	$(PYTHON) scripts/build_parcels_full_data.py

# Run the full viz-data pipeline. After this, viz/src/data/* is up to date.
viz-data: build-geojson build-cohort-history build-parcels-full

viz-install:
	cd viz && npm install

viz-dev: viz-install
	cd viz && npm run dev
