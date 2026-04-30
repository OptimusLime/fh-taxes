#!/usr/bin/env bash
# Overnight OPRS comprehensive collection — 8 hourly batches with jitter.
#
# Plan: 1,961 remaining parcels / 8 batches ≈ 246 parcels per batch.
# Each batch ~2,100 HTTP reqs at 2.3 r/s effective ≈ 15 min wall.
# Hourly cadence with ±5 min jitter on start time spreads the footprint.
#
# Usage:
#   nohup ./temporary_scripts/run_overnight.sh > /dev/null 2>&1 &
#   tail -f temporary_scripts/sandbox/overnight_*/SUMMARY.log
#
# Resumes cleanly: collector is idempotent (atomic writes + content validation
# + .no_sale markers). Re-running skips already-cached components for free.

set -uo pipefail  # NOT -e — auto-abort from collector should not kill the script
cd "$(dirname "$0")/.."

TOTAL_BATCHES=8
PARCELS_FILE="data/processed/parcels.parquet"
RUN_ID="$(date +%Y%m%d_%H%M)"
LOG_DIR="temporary_scripts/sandbox/overnight_${RUN_ID}"
mkdir -p "$LOG_DIR"
SUMMARY="$LOG_DIR/SUMMARY.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] $*" | tee -a "$SUMMARY"; }

log "OVERNIGHT RUN START — $TOTAL_BATCHES batches, target finish ~06:00 ET"
log "log dir: $LOG_DIR"
log "parcels: $(uv run python -c "import pandas as pd; print(len(pd.read_parquet('$PARCELS_FILE')))")"

for i in $(seq 1 "$TOTAL_BATCHES"); do
  # Batch 1 starts immediately. Subsequent batches sleep until next hour mark
  # ± 5 min jitter so the start time isn't exactly :00 of every hour.
  if [ "$i" -gt 1 ]; then
    JITTER=$(( (RANDOM % 601) - 300 ))  # -300..+300 sec (±5 min)
    # Compute "next top of hour" in epoch seconds (BSD date / macOS).
    NEXT_HOUR_TS=$(date -v+1H -v0M -v0S +%s)
    NOW_TS=$(date +%s)
    SLEEP_SEC=$(( NEXT_HOUR_TS - NOW_TS + JITTER ))
    if [ "$SLEEP_SEC" -lt 60 ]; then
      # If we're already past the target hour mark (long batch), still wait at
      # least 60s before the next run to avoid hammering.
      SLEEP_SEC=60
    fi
    log "batch $i: sleeping ${SLEEP_SEC}s (jitter=${JITTER}s) until next window"
    sleep "$SLEEP_SEC"
  fi

  log "batch $i/$TOTAL_BATCHES START"
  BATCH_LOG="$LOG_DIR/batch_${i}.log"

  # Add small per-run rate jitter too: 2.7-3.3 req/s.
  RATE_JITTER=$(awk "BEGIN{srand($i$$); printf \"%.2f\", 2.7 + rand()*0.6}")

  if uv run python datasets/collect_oprs.py \
      --parcels-from "$PARCELS_FILE" \
      --output-dir data/raw/oprs_prc \
      --mode comprehensive \
      --batch 2500 \
      --rate "$RATE_JITTER" \
      --jitter-pct 0.3 \
      --max-error-rate 0.15 \
      > "$BATCH_LOG" 2>&1; then
    BATCH_END_LINE=$(grep "batch end:" "$BATCH_LOG" | tail -1)
    log "batch $i DONE @ rate=$RATE_JITTER — $BATCH_END_LINE"
  else
    EXIT=$?
    log "batch $i FAILED (exit=$EXIT) — see $BATCH_LOG"
    log "  continuing anyway; collector is idempotent so next batch will retry"
  fi

  # Snapshot cache coverage after each batch.
  CACHED=$(find data/raw/oprs_prc -mindepth 2 -maxdepth 2 -name "taxlist_2026.pdf" 2>/dev/null | wc -l | tr -d ' ')
  log "  coverage: $CACHED / 2061 parcels have taxlist_2026.pdf"
done

log "OVERNIGHT RUN COMPLETE"
log "final coverage:"
uv run python -c "
import os, glob
parcels = glob.glob('data/raw/oprs_prc/*/')
full = sum(1 for d in parcels if os.path.exists(d+'m4.html') and os.path.exists(d+'prc.pdf') and os.path.exists(d+'ch75.pdf') and os.path.exists(d+'taxlist_2026.pdf'))
print(f'  parcel dirs: {len(parcels)}')
print(f'  fully cached (m4 + prc + ch75 + taxlist_2026): {full}')
" 2>&1 | tee -a "$SUMMARY"
