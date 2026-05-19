#!/usr/bin/env bash
# Verify that config/hermes-profile.yaml in this repo has not drifted from
# the canonical one in ai-beautyos. The canonical profile lives in the
# Web/API repo because that's where the protocol contract is owned.
#
# Sources of the canonical:
#   1. local path via $AI_BEAUTYOS_PATH (preferred in dev)
#   2. raw.githubusercontent.com via curl (CI fallback)
#
# Exit:
#   0  in-sync
#   1  drift detected (prints the diff)
#   2  unable to fetch canonical

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL="$ROOT/config/hermes-profile.yaml"

if [ ! -f "$LOCAL" ]; then
  echo "[drift] FATAL: $LOCAL not present" >&2
  exit 2
fi

CANONICAL_TMP=$(mktemp)
trap 'rm -f "$CANONICAL_TMP"' EXIT

if [ -n "${AI_BEAUTYOS_PATH:-}" ] && [ -f "$AI_BEAUTYOS_PATH/config/hermes-profile.yaml" ]; then
  cp "$AI_BEAUTYOS_PATH/config/hermes-profile.yaml" "$CANONICAL_TMP"
  echo "[drift] canonical source: $AI_BEAUTYOS_PATH (local)"
else
  URL="https://raw.githubusercontent.com/CHINGBOH/ai-beautyos/main/config/hermes-profile.yaml"
  if ! curl -fsSL "$URL" -o "$CANONICAL_TMP"; then
    echo "[drift] FATAL: cannot fetch $URL" >&2
    exit 2
  fi
  echo "[drift] canonical source: $URL"
fi

if diff -u "$CANONICAL_TMP" "$LOCAL" > /tmp/profile.diff; then
  echo "[drift] ✓ profile in sync with canonical"
  exit 0
else
  echo "[drift] ✗ profile drift detected:"
  cat /tmp/profile.diff
  exit 1
fi
