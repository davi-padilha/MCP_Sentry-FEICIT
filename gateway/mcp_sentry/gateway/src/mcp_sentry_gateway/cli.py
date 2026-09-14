import argparse, json, sys
from pathlib import Path
from .core import SentryError, approve, inspect, run, accept_current, promote_execution_envelope
from .review import approve_review_execution
def main():
    p=argparse.ArgumentParser(description="MCP Sentry local core"); p.add_argument("command",choices=("approve","inspect","run","accept-current","promote-execution-envelope","approve-review-execution")); p.add_argument("--manifest",required=True,type=Path); p.add_argument("--store",required=True,type=Path); p.add_argument("--human-confirmation"); p.add_argument("--review-id"); p.add_argument("--reviewed-hash"); p.add_argument("--dossier-hash"); a=p.parse_args()
    try:
        action={"approve":approve,"inspect":inspect,"run":run,"accept-current":accept_current}.get(a.command)
        result = (promote_execution_envelope(a.manifest, a.store, a.human_confirmation) if a.command == "promote-execution-envelope" else approve_review_execution(a.manifest, a.store, a.review_id, a.reviewed_hash, a.dossier_hash, a.human_confirmation) if a.command == "approve-review-execution" else action(a.manifest,a.store))
        print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)); return 0
    except (OSError,ValueError,SentryError) as exc: print(f"mcp-sentry: blocked: {exc}",file=sys.stderr); return 2
if __name__ == "__main__": raise SystemExit(main())
