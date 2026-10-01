"""Smoke-test deployed Claude connectors without invoking any Donna action.

Usage: python verificar_interfaces_claude.py PATH_TO_CLAUDE_CONFIG
Only initializes/catalogs the executor; reads status/diff on the reviewer.
Does not record a verdict, authorize execution, or read OAuth file contents.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def exchange(process, request_id, method, params=None):
    message = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        message["params"] = params
    process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()
    response = json.loads(process.stdout.readline())
    if "error" in response:
        raise RuntimeError(response["error"])
    assert response["id"] == request_id
    return response["result"]


def inspect_connector(entry, review):
    environment = os.environ.copy()
    environment.update(entry.get("env", {}))
    with subprocess.Popen([entry["command"], *entry["args"]], stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, encoding="utf-8", env=environment) as process:
        try:
            initialized = exchange(process, 1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "local-review-smoke", "version": "1"}})
            assert initialized["serverInfo"]["name"] == ("mcp-sentry-review" if review else "mcp-sentry-donna")
            process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            process.stdin.flush()
            catalog = exchange(process, 2, "tools/list")["tools"]
            names = {tool["name"] for tool in catalog}
            if not review:
                assert "enviar_email" in names and not any(name.startswith("sentry_") for name in names)
                return {"tools": len(names), "Donna_actions_called": 0}
            assert names == {"sentry_security_status", "sentry_review_current_block", "sentry_review_evidence", "sentry_record_assessment"}
            response = exchange(process, 3, "tools/call", {"name": "sentry_review_current_block", "arguments": {}})
            assert not response.get("isError"), response["structuredContent"]
            evidence = response["structuredContent"]
            assert len(evidence["changes"]) == evidence["total_changes"]
            return {"tools": len(names), "status": evidence["status"], "review_id": evidence["review_id"], "pages_read": "all", "changed_paths": [item["path"] for item in evidence["changes"]], "Donna_actions_called": 0}
        finally:
            process.stdin.close()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)


def main():
    config = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))["mcpServers"]
    executor, reviewer = config["mcp_sentry_donna"], config["mcp_sentry_review"]
    assert not reviewer.get("env"), "Review must not receive Donna OAuth settings"
    for flag in ("--manifest", "--store"):
        assert executor["args"][executor["args"].index(flag) + 1] == reviewer["args"][reviewer["args"].index(flag) + 1]
    store = Path(reviewer["args"][reviewer["args"].index("--store") + 1])
    baseline = store / "versao-aprovada.json"
    before = hashlib.sha256(baseline.read_bytes()).hexdigest()
    report = {"execution": inspect_connector(executor, False), "review": inspect_connector(reviewer, True)}
    assert before == hashlib.sha256(baseline.read_bytes()).hexdigest(), "Baseline changed"
    report["baseline_preserved"] = True
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
