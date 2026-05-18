#!/usr/bin/env bash
# Convenience wrapper around `mirage-eval sweep` with sensible defaults.
#
# Usage:
#   ./scripts/run_sweep.sh                                  # L1, gpt-5-mini, 1 seed, primary tasks
#   ./scripts/run_sweep.sh --models gpt-5-mini,gpt-5 --seeds 1,2,3
#   ./scripts/run_sweep.sh --surface l2                     # real Slack + Google
#   ./scripts/run_sweep.sh --include-adversarial            # add the 4 adversarial variants
set -euo pipefail
cd "$(dirname "$0")/.."

SCENARIO="${SCENARIO:-onboarding_it}"
MODELS="${MODELS:-gpt-5-mini}"
SEEDS="${SEEDS:-1}"
SURFACE="${SURFACE:-l1}"
CONCURRENCY="${CONCURRENCY:-2}"

uv run mirage-eval sweep \
  --scenario "$SCENARIO" \
  --models "$MODELS" \
  --seeds "$SEEDS" \
  --surface "$SURFACE" \
  --concurrency "$CONCURRENCY" \
  --yes \
  "$@"
