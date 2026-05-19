#!/usr/bin/env bash
# Sync upstream Hermes into a sibling directory (not vendored into this repo).
#
# This script:
#   1. Reads UPSTREAM_HERMES.txt for the pinned repo + SHA
#   2. Clones / fetches into $HERMES_CHECKOUT (default: ./hermes/)
#   3. Checks out the pinned SHA
#   4. Verifies the working tree matches the pin
#
# The hermes/ directory is .gitignored — we do NOT vendor upstream code.
# The Dockerfile.full target uses this checkout as build context for the
# final image; in dev you can also `python3 bootstrap.py` after running
# this script (set HERMES_PATH=./hermes).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
source <(grep -E '^(UPSTREAM_REPO|UPSTREAM_SHA|UPSTREAM_VERSION)=' UPSTREAM_HERMES.txt)

CHECKOUT="${HERMES_CHECKOUT:-$ROOT/hermes}"

echo "[sync-upstream] repo=$UPSTREAM_REPO"
echo "[sync-upstream] pinned SHA=$UPSTREAM_SHA  version=$UPSTREAM_VERSION"
echo "[sync-upstream] checkout dir=$CHECKOUT"

if [ ! -d "$CHECKOUT/.git" ]; then
  echo "[sync-upstream] fresh clone…"
  git clone --filter=blob:none "$UPSTREAM_REPO" "$CHECKOUT"
fi

cd "$CHECKOUT"
git fetch --quiet origin

if ! git rev-parse --verify "$UPSTREAM_SHA^{commit}" >/dev/null 2>&1; then
  echo "[sync-upstream] FATAL: pinned SHA $UPSTREAM_SHA not in $UPSTREAM_REPO" >&2
  exit 1
fi

git -c advice.detachedHead=false checkout --quiet "$UPSTREAM_SHA"

ACTUAL=$(git rev-parse HEAD)
if [ "$ACTUAL" != "$UPSTREAM_SHA" ]; then
  echo "[sync-upstream] FATAL: HEAD=$ACTUAL != pin=$UPSTREAM_SHA" >&2
  exit 1
fi

echo "[sync-upstream] ✓ checkout matches pin (${ACTUAL:0:12})"
echo "[sync-upstream] next: export HERMES_PATH=$CHECKOUT && python3 bootstrap.py"
