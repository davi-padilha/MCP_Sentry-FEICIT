"""Opt-in integration smoke test with an already installed, exact server version.

Uses disposable configuration and state inside --lab. Never edits a client.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mcp_sentry_gateway.core import approve, capture, inspect
from mcp_sentry_gateway.gateway import StdioGateway
from mcp_sentry_gateway.onboarding import prepare_codex
from mcp_sentry_gateway.operator import decide
from mcp_sentry_gateway.profiles import installed_plan
from mcp_sentry_gateway.review import ensure_pending, submit_verdict


def run(profile, root, runtime, version, lab):
    lab.mkdir(parents=True, exist_ok=False)
    config = lab / "config"
    config.mkdir()
    data = lab / "data"
    data.mkdir()
    if profile == "git":
        import subprocess
        subprocess.run([os.environ["GIT_PYTHON_GIT_EXECUTABLE"], "init", str(data)], check=True, capture_output=True)
    (data / "input.txt").write_text("conteudo ficticio sentry\n", encoding="utf-8")
    manifest, store = config / "manifest.json", lab / "state"
    roots, command = installed_plan(profile, root, runtime, version, data)
    prepare_codex(SimpleNamespace(project_root=root, inspect_root=roots, manifest=manifest,
        store=store, fragment=config / "codex.toml", name=profile, backend_command=command,
        passthrough_name=["PATH", "GIT_PYTHON_GIT_EXECUTABLE"] if profile == "git" else []))
    approve(manifest, store)
    entry = root / ("node_modules/@modelcontextprotocol/server-filesystem/dist/index.js" if profile == "filesystem" else "mcp_server_git/server.py")
    original = entry.read_bytes()
    method, arguments = ("read_text_file", {"path": str(data / "input.txt")}) if profile == "filesystem" else ("git_status", {"repo_path": str(data)})
    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": method, "arguments": arguments}}
    results = []
    def call(expect_ok):
        gateway = StdioGateway(manifest, store, interface="execution")
        try:
            response = gateway.handle(request)
            if expect_ok:
                assert not response["result"].get("isError"), response
                assert gateway.backend.process is not None, response
                assert gateway.backend.copy_root != root
                assert (gateway.backend.copy_root / entry.relative_to(root)).read_bytes() == entry.read_bytes()
                assert "conteudo ficticio sentry" in json.dumps(response) if profile == "filesystem" else "input.txt" in json.dumps(response)
            else:
                assert gateway.backend.lifecycle.snapshot()["spawn_attempts"] == 0
                assert response["result"]["structuredContent"]["status"] == "security_review_required", response
            results.append({"ok": expect_ok, "protocol": gateway.backend.backend_protocol_version,
                            "spawn_attempts": gateway.backend.lifecycle.snapshot()["spawn_attempts"], "response": response})
        finally:
            gateway.backend.close()
    try:
        call(True)
        entry.write_bytes(original + (b"\n// smoke local update\n" if profile == "filesystem" else b"\n# smoke local update\n"))
        call(False)
        record, _ = ensure_pending(manifest, store)
        submit_verdict(manifest, store, {"review_id": record["review_id"], "reviewed_hash": record["dossier"]["current_hash"],
            "dossier_hash": record["dossier"]["dossier_hash"], "policy_version": record["policy_version"],
            "decision": "allow", "justification": "Controlled smoke fixture: appended comment only", "risks": []})
        decide(manifest, store, "accept", input_fn=lambda: "ACEITAR", output=lambda _: None)
        assert inspect(manifest, store)["status"] == "unchanged"
        call(True)
    finally:
        entry.write_bytes(original)
    report = {"profile": profile, "version": version, "runtime": str(runtime),
              "protected_files": len(capture(manifest)["files"]) - 1, "results": results,
              "client": "in-process StdioGateway; no desktop client", "update": "controlled comment, not published V2"}
    (lab / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("filesystem", "git"), required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--lab", type=Path, required=True)
    args = parser.parse_args()
    run(args.profile, args.root.resolve(), args.runtime.resolve(), args.version, args.lab.resolve())
