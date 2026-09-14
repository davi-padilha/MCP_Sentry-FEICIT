"""Controlled JSON-RPC stdio MCP fixture used only by T3 integration tests."""
import json
import sys

initialized = False

for line in sys.stdin:
    request = json.loads(line)
    if request.get("method") == "initialize": result = {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}}, "serverInfo": {"name": "minimum", "version": "1"}}
    elif request.get("method") == "notifications/initialized":
        initialized = True
        continue
    elif request.get("method") == "tools/call" and request.get("params", {}).get("name") == "ping" and initialized: result = {"content": [{"type": "text", "text": "pong"}]}
    else: result = {"isError": True, "content": [{"type": "text", "text": "unsupported"}]}
    if "id" in request:
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}, separators=(",", ":")) + "\n"); sys.stdout.flush()
