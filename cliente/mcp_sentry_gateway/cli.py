"""Operator commands. The conversational MCP interface never exposes them."""

import argparse
import json
import sys
from pathlib import Path

from .core import SentryError, accept_current, approve, inspect, promote_execution_envelope
from .review import approve_review_execution


def main():
    if len(sys.argv) > 1 and sys.argv[1] in {"prepare-codex", "doctor"}:
        from .onboarding import main as onboarding_main
        return onboarding_main(sys.argv[1:])
    parser = argparse.ArgumentParser(description="MCP Sentry local operator commands")
    parser.add_argument("command", choices=(
        "approve", "inspect", "accept-current", "promote-execution-envelope",
        "approve-review-execution",
    ))
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--human-confirmation")
    parser.add_argument("--review-id")
    parser.add_argument("--reviewed-hash")
    parser.add_argument("--dossier-hash")
    args = parser.parse_args()

    try:
        if args.command == "promote-execution-envelope":
            result = promote_execution_envelope(args.manifest, args.store, args.human_confirmation)
        elif args.command == "approve-review-execution":
            result = approve_review_execution(
                args.manifest, args.store, args.review_id, args.reviewed_hash,
                args.dossier_hash, args.human_confirmation,
            )
        else:
            action = {"approve": approve, "inspect": inspect, "accept-current": accept_current}[args.command]
            result = action(args.manifest, args.store)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, SentryError) as exc:
        print(f"mcp-sentry: blocked: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
