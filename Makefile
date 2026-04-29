.PHONY: help install acquire acquire-njgin acquire-dlgs acquire-sr1a ingest validate all clean test

PYTHON := uv run python
TODAY := $(shell date +%Y-%m-%d)

help:
	@echo "fairhaven_tax pipeline targets:"
	@echo "  make install         - uv sync (install deps)"
	@echo "  make acquire         - download all three raw datasets to data/raw/<source>/$(TODAY)/"
	@echo "  make acquire-njgin   - download Monmouth Parcels+MOD-IV FGDB only"
	@echo "  make acquire-dlgs    - download DLGS Property Tax Tables only"
	@echo "  make acquire-sr1a    - download SR1A 2018-2025 only"
	@echo "  make ingest          - parse raw -> data/processed/ parquet (Plan 2)"
	@echo "  make validate        - run validation gate (Plan 2)"
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

ingest:
	$(PYTHON) -m fairhaven_tax.cli ingest

validate:
	$(PYTHON) -m fairhaven_tax.cli validate

all: acquire ingest validate

test:
	uv run pytest -q

clean:
	rm -rf data/processed/
