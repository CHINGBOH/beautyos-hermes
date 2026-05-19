# Upstream Hermes sync strategy

This repo is a **thin wrapper** around
[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).
We pin upstream by exact commit SHA in `UPSTREAM_HERMES.txt` and check
it out into `./hermes/` (gitignored) on demand. We do **not** fork or
vendor upstream source.

## Pinning model

`UPSTREAM_HERMES.txt` is the single source of truth:

```
UPSTREAM_REPO=https://github.com/NousResearch/hermes-agent.git
UPSTREAM_SHA=683698742852ce0455f3a07b12c772c786d5a2ae
UPSTREAM_VERSION=0.14.0
```

`scripts/sync-upstream.sh` reads this file, clones/fetches into
`./hermes/`, and asserts `HEAD == UPSTREAM_SHA`. CI runs the same
script to fail the build on drift.

## Local development

```bash
# 1. Sync upstream to the pinned SHA
./scripts/sync-upstream.sh

# 2. Run the bootstrap with handoff enabled
export BEAUTYOS_BASE=http://localhost:3000
export BEAUTYOS_TOOL_BASE=http://localhost:5001
export HERMES_PATH=$(pwd)/hermes
python3 bootstrap.py [hermes-cli-args ...]
```

If all 8 smoke stages pass, `bootstrap.py` chdirs into `$HERMES_PATH`
and `exec`s `python3 cli.py [args...]`. If `HERMES_PATH` is unset,
bootstrap exits 0 after the smoke (scaffold / CI smoke mode).

## Rolling upstream forward

```bash
# 1. From a clean state
git checkout main && git pull
cd hermes && git fetch && git log --oneline origin/main -20  # pick the new SHA
cd ..

# 2. Bump the pin
sed -i "s/^UPSTREAM_SHA=.*/UPSTREAM_SHA=<new-sha>/" UPSTREAM_HERMES.txt
sed -i "s/^UPSTREAM_VERSION=.*/UPSTREAM_VERSION=<new-version>/" UPSTREAM_HERMES.txt

# 3. Re-sync + re-smoke
./scripts/sync-upstream.sh
# (run bootstrap.py against a live ai-beautyos compose stack)

# 4. Commit + PR
git checkout -b sync/upstream-$(date +%Y%m%d)
git commit -am "sync: bump upstream Hermes to <new-sha> (<new-version>)"
gh pr create --base main --title "sync: upstream Hermes <new-sha>"
```

## Build artefact

The Dockerfile currently ships **only the wrapper** (bootstrap.py +
config/). For an image that bundles upstream Hermes too, run
`scripts/sync-upstream.sh` first, then build with a Dockerfile that
`COPY hermes/ /opt/hermes/` and sets `ENV HERMES_PATH=/opt/hermes`.
We deliberately don't bake this into the default Dockerfile yet —
upstream pulls Playwright + ffmpeg + Node and balloons the image
past 2 GB; tracked as a follow-up after Phase-3 hardening.

## What we MAY modify

- `bootstrap.py` — protocol implementation, our code
- `config/hermes-profile.yaml` — BeautyOS-specific bootstrap config
  (mirror of `ai-beautyos/config/hermes-profile.yaml`)
- `UPSTREAM_HERMES.txt` — the pin
- `docs/`, `Dockerfile`, `.github/workflows/`, `scripts/`

## What we MUST NOT modify

- Anything under `./hermes/` — that's the synced upstream checkout.
  Patches go upstream via NousResearch/hermes-agent.
- The protocol shape defined in
  `ai-beautyos/docs/architecture/hermes-adapter.md` — that contract
  lives in the other repo. Coordinate via PR if it must change.

## Profile drift detection

`scripts/check-profile-drift.sh` compares our
`config/hermes-profile.yaml` against the canonical one in
`ai-beautyos`. Sources:

- `$AI_BEAUTYOS_PATH/config/hermes-profile.yaml` (dev, preferred)
- `raw.githubusercontent.com/CHINGBOH/ai-beautyos/main/...` (CI)

On drift the script exits 1 and prints the diff. Either re-sync the
profile here or land a coordinated PR in ai-beautyos first.
