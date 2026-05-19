# beautyos-hermes

Custom Hermes runtime wrapper for [BeautyOS](https://github.com/CHINGBOH/ai-beautyos).
A **thin wrapper** that boots upstream [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
against the BeautyOS System Registry + MCP Tool Server.

## What lives here

* Upstream Hermes tracked as a Git remote — rebased, never forked.
* `bootstrap.py` — the BeautyOS-aware boot sequence implementing the
  adapter protocol from `ai-beautyos/docs/architecture/hermes-adapter.md`.
* `config/hermes-profile.yaml` — the BeautyOS profile (copy of the
  canonical one in `ai-beautyos/config/hermes-profile.yaml`; rebased
  via sync workflow).
* `Dockerfile` — published as a separate image, deployed alongside
  the BeautyOS compose stack.

## What does NOT live here

* BeautyOS DB schema, business tools, tool implementations — those
  stay in [ai-beautyos](https://github.com/CHINGBOH/ai-beautyos).
* LLM API keys — environment-only at deploy time.
* Hermes upstream patches — track upstream, don't fork internals.

See `ai-beautyos/docs/architecture/repo-strategy.md` for the full
dual-repo contract.

## Quick start

```bash
# 1. Point at a running BeautyOS stack
export BEAUTYOS_BASE=http://localhost:3000        # System Registry
export TOOL_BASE=http://localhost:5001            # MCP Tool Server
export BEAUTYOS_TENANT_ID=00000000-0000-0000-0000-000000000001

# 2. Boot — validates manifest version, fetches tools/permissions,
#    smoke-invokes one read-only tool, then hands off to Hermes
python3 bootstrap.py
```

Exit codes:

| Code | Meaning                                          |
|------|--------------------------------------------------|
| 0    | bootstrap green, ready to enter Hermes run loop  |
| 1    | bootstrap network failure (manifest / tools)     |
| 2    | manifest major-version mismatch                  |
| 3    | tool invoke failed                               |

## Upstream Hermes sync

See `docs/upstream-sync.md`.

## License

MIT. Upstream Hermes is also MIT.
