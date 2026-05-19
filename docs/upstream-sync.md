# Upstream Hermes sync strategy

This repo is a **thin wrapper** around
[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).
We track upstream via Git remote + rebase. We do **not** fork.

## One-time setup

```bash
git remote add upstream https://github.com/NousResearch/hermes-agent.git
git fetch upstream
```

## Pulling upstream changes

```bash
# 1. Sync local main with our origin
git checkout main
git pull origin main

# 2. Create a sync branch
git checkout -b sync/upstream-$(date +%Y%m%d)

# 3. Fetch + rebase against upstream main
git fetch upstream
git rebase upstream/main

# 4. Resolve conflicts ONLY in our adapter files
#    (bootstrap.py, config/hermes-profile.yaml, docs/, Dockerfile).
#    NEVER edit upstream source files. If upstream changed the
#    Hermes entrypoint or API surface, update bootstrap.py to match.

# 5. Push the sync branch + open PR
git push origin sync/upstream-$(date +%Y%m%d)
gh pr create --base main --title "sync: upstream Hermes $(git rev-parse --short upstream/main)"
```

## Build artefact

The Dockerfile (Phase-3 step 4, not yet shipped) will:

1. `FROM` an upstream-Hermes base image (or build from upstream tag)
2. `COPY` bootstrap.py + config/ into a known path
3. set `ENTRYPOINT ["python3", "/app/bootstrap.py"]`
4. set `HERMES_ENTRYPOINT=/opt/hermes/cli.py` so bootstrap hands off
   after the green check

## What we MAY modify

- `bootstrap.py` — protocol implementation, our code
- `config/hermes-profile.yaml` — BeautyOS-specific bootstrap config
  (copy of `ai-beautyos/config/hermes-profile.yaml`)
- `docs/` — our documentation
- `Dockerfile` — our image recipe
- `.github/workflows/` — our CI

## What we MUST NOT modify

- Anything that comes from upstream Hermes — file path, name, layout.
- The protocol shape defined in
  `ai-beautyos/docs/architecture/hermes-adapter.md` — that contract
  lives in the other repo. Coordinate via PR if it must change.

## Profile drift detection

CI runs `scripts/check-profile-drift.sh` which compares our
`config/hermes-profile.yaml` against the canonical one in
`ai-beautyos` (by git URL). On drift, the build fails until either:

- the wrapper re-syncs the profile, OR
- a coordinated PR in ai-beautyos updates the canonical first.
