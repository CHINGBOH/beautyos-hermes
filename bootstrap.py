#!/usr/bin/env python3
"""BeautyOS-aware Hermes bootstrap.

Implements the startup sequence specified in
`ai-beautyos/docs/architecture/hermes-adapter.md`:

  1. read config/hermes-profile.yaml
  2. GET  $BEAUTYOS_BASE/system/manifest      (version compat check)
  3. GET  $BEAUTYOS_BASE/system/tools         (catalogue from registry)
  4. GET  $BEAUTYOS_BASE/system/permissions   (allow / forbid)
  5. GET  $TOOL_BASE/tools                    (live MCP catalogue)
  6. POST $TOOL_BASE/tools/<low-risk>/invoke  (smoke invoke)
  7. assert requiresConfirm tool returns 412 without confirmed=true
  8. on success, exec into the upstream Hermes entrypoint

Exit codes:
  0  green, hands off to Hermes run loop
  1  bootstrap network failure
  2  manifest major-version mismatch
  3  tool invoke failed
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib import error, request

try:
    import yaml  # type: ignore
except ImportError:
    print("FATAL: PyYAML not installed (pip install pyyaml)", file=sys.stderr)
    sys.exit(1)

PROFILE_PATH = Path(__file__).resolve().parent / "config" / "hermes-profile.yaml"

BEAUTYOS_BASE = os.environ.get("BEAUTYOS_BASE", "http://web:3000")
TOOL_BASE = os.environ.get("TOOL_BASE", "http://tool-server:5001")
TENANT_ID = os.environ.get("BEAUTYOS_TENANT_ID", "")
AGENT_ID = os.environ.get("BEAUTYOS_AGENT_ID", "hermes-bootstrap")


def log(stage: str, **detail: Any) -> None:
    record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "stage": stage}
    record.update(detail)
    print(json.dumps(record), flush=True)


def fail(code: int, reason: str, **extra: Any) -> None:
    log("fatal", reason=reason, **extra)
    sys.exit(code)


def req_headers() -> dict[str, str]:
    rid = f"boot_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
    return {
        "x-tenant-id": TENANT_ID or "00000000-0000-0000-0000-000000000001",
        "x-agent-id": AGENT_ID,
        "x-request-id": rid,
        "x-trace-id": rid,
    }


def get_json(url: str, headers: dict[str, str] | None = None) -> Any:
    req = request.Request(url, headers=headers or {})
    with request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def post_json(url: str, body: dict[str, Any], headers: dict[str, str]) -> tuple[int, Any]:
    data = json.dumps(body).encode("utf-8")
    hdrs = {**headers, "content-type": "application/json"}
    req = request.Request(url, data=data, headers=hdrs, method="POST")
    try:
        with request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body_text)
        except json.JSONDecodeError:
            parsed = {"raw": body_text[:200]}
        return e.code, parsed


_RANGE = re.compile(r">=\s*(\d+)\.\d+\.\d+\s*<\s*(\d+)\.\d+\.\d+")


def version_compatible(version: str, want_range: str | None) -> bool:
    if not want_range:
        return True
    m = _RANGE.match(want_range)
    if not m:
        return True  # unparseable range — don't block
    major = int(version.split(".")[0])
    return int(m.group(1)) <= major < int(m.group(2))


def main() -> None:
    log("boot", base=BEAUTYOS_BASE, toolBase=TOOL_BASE, tenantId=TENANT_ID or "<default>", agentId=AGENT_ID)

    with open(PROFILE_PATH, encoding="utf-8") as f:
        profile = yaml.safe_load(f)
    want_range = (profile.get("compatible") or {}).get("beautyosManifest")
    log("profile.loaded", policyFile=(profile.get("policy") or {}).get("file"), wantRange=want_range)

    endpoints = ((profile.get("beautyos") or {}).get("endpoints")) or {}
    manifest_path = endpoints.get("manifest", "/system/manifest")
    tools_path = endpoints.get("tools", "/system/tools")
    perms_path = endpoints.get("permissions", "/system/permissions")

    # 1) manifest + version compat
    try:
        manifest = get_json(BEAUTYOS_BASE + manifest_path)
    except Exception as e:
        fail(1, "manifest fetch failed", err=str(e))
    version = (manifest.get("meta") or {}).get("version")
    log("manifest.ok", version=version)
    if want_range and not version_compatible(version, want_range):
        fail(2, "manifest version incompatible", version=version, wantRange=want_range)

    # 2) registry catalogues
    sys_tools = get_json(BEAUTYOS_BASE + tools_path)
    log("system.tools", count=len((sys_tools or {}).get("tools") or []))

    perms = get_json(BEAUTYOS_BASE + perms_path)
    log("system.permissions", keys=list((perms or {}).keys()))

    # 3) live tool-server catalogue
    live = get_json(TOOL_BASE + "/tools")
    tools = (live or {}).get("tools") or []
    names = [t["name"] for t in tools]
    log("toolserver.tools", count=len(tools), names=names)

    # 4) smoke invoke — pick first low-risk read-only tool by config
    target = next((t["name"] for t in tools if t.get("risk") == "low" and t.get("access") == "ro"), None)
    if not target:
        fail(3, "no low-risk read-only tool in catalogue")
    hdrs = req_headers()
    log("invoke.start", tool=target, requestId=hdrs["x-request-id"])
    status, out = post_json(f"{TOOL_BASE}/tools/{target}/invoke", {"input": {}}, hdrs)
    if status != 200:
        fail(3, "invoke failed", status=status, body=out)
    log("invoke.ok", tool=out.get("tool"), durationMs=out.get("durationMs"), requestId=hdrs["x-request-id"])

    # 5) confirm-required tool must 412 without confirmed
    confirm_target = next((t["name"] for t in tools if t.get("requiresConfirm")), None)
    if confirm_target:
        hdrs2 = req_headers()
        status, out = post_json(
            f"{TOOL_BASE}/tools/{confirm_target}/invoke",
            {"input": {"customerId": "cust_demo"}},
            hdrs2,
        )
        if status != 412:
            fail(3, "confirm-required tool did not return 412", tool=confirm_target, got=status)
        log("invoke.confirm_blocked.ok", tool=confirm_target, status=412)

    log("done", ok=True)

    # 6) Hand off to upstream Hermes if HERMES_PATH points at a synced
    # checkout (see scripts/sync-upstream.sh). bootstrap.py forwards any
    # CLI args it received to upstream's cli.py and chdirs into the
    # upstream directory first so its relative imports resolve.
    hermes_path = os.environ.get("HERMES_PATH")
    if hermes_path:
        cli = os.path.join(hermes_path, "cli.py")
        if not os.path.exists(cli):
            log("handoff.skip", reason="HERMES_PATH set but cli.py missing", path=cli)
            return
        log("handoff", hermesPath=hermes_path, cli=cli, version=_read_upstream_version())
        os.chdir(hermes_path)
        os.execv(sys.executable, [sys.executable, cli, *sys.argv[1:]])
    else:
        log("handoff.skip", reason="HERMES_PATH not set; run scripts/sync-upstream.sh and re-run with HERMES_PATH=./hermes")


def _read_upstream_version() -> str:
    pin = Path(__file__).resolve().parent / "UPSTREAM_HERMES.txt"
    if not pin.exists():
        return "unknown"
    for line in pin.read_text(encoding="utf-8").splitlines():
        if line.startswith("UPSTREAM_VERSION="):
            return line.split("=", 1)[1].strip()
    return "unknown"


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # pragma: no cover
        fail(1, "unexpected", err=repr(e))
