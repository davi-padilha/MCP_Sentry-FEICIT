"""Interactive update decisions, available only to the local operator."""
import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timezone

from .core import SentryError, accept_current, capture, canon, digest, execution_envelope, load_execution_envelope, promote_execution_envelope, write
from .review import ensure_pending, approve_review_execution


def decide(manifest, store, action, *, input_fn=input, output=print):
    record, result = ensure_pending(manifest, store)
    if record is None or record["status"] != "awaiting_human_approval":
        raise SentryError("a versão atual precisa de parecer allow registrado e vigente")
    shown = record["dossier"]
    output(json.dumps({"review_id": record["review_id"], "version_hash": shown["current_hash"],
                       "assessment": record["verdict"], "coverage": shown.get("coverage", {}),
                       "configuration": shown["configuration"], "changes": [
                           {"path": c["path"], "kind": c["kind"]} for c in shown["changes"]]},
                      ensure_ascii=False, indent=2))
    confirmations = {"once": "AUTORIZAR", "accept": "ACEITAR", "catalog": "DESCOBRIR", "envelope": "PROMOVER"}
    if action == "catalog":
        output("DESCOBRIR autoriza iniciar uma cópia desta versão revisada uma vez para consultar o catálogo.")
    elif action == "envelope":
        output("PROMOVER aprova somente a configuração exibida, incluindo as raízes; não aprova código nem inicia o servidor.")
    else:
        output("AUTORIZAR libera um início; ACEITAR torna esta versão a referência permanente.")
    output(f"Digite {confirmations[action]} para confirmar, ou Enter para cancelar:")
    if input_fn() != confirmations[action]:
        return {"status": "cancelled"}
    fresh, _ = ensure_pending(manifest, store)
    if (fresh is None or fresh["review_id"] != record["review_id"] or
            fresh["status"] != "awaiting_human_approval"):
        raise SentryError("estado ou parecer mudou desde a revisão exibida")
    if action == "envelope":
        return promote_execution_envelope(manifest, store, "PROMOTE_EXECUTION_ENVELOPE", expected_hash=shown["current_hash"])
    if execution_envelope(capture(manifest)) != load_execution_envelope(store):
        raise SentryError("envelope de execução mudou; requer promoção humana separada")
    if action == "once":
        return approve_review_execution(manifest, store, record["review_id"], shown["current_hash"],
                                        shown["dossier_hash"], "APPROVE_REVIEW_EXECUTION")
    if action == "accept":
        return accept_current(manifest, store, expected_hash=shown["current_hash"])

    from .gateway import BackendSession
    from .onboarding import discover_tools
    audit = {"review_id": record["review_id"], "reviewed_hash": shown["current_hash"],
             "authorized_at": datetime.now(timezone.utc).isoformat(), "status": "operator_authorized"}
    audit_path = store / f"descoberta-catalogo-{record['review_id']}.json"
    write(audit_path, audit)
    session = BackendSession(manifest, store)
    try:
        command, cwd, environment = session._copy_and_spawn(shown["current_hash"], spawn=False)
        tools = discover_tools(command, cwd, [], environment, session.backend_request_timeout_seconds)
        write(audit_path, {**audit, "status": "completed", "tools": len(tools)})
    except (OSError, ValueError):
        write(audit_path, {**audit, "status": "failed"})
        raise
    finally:
        session.close()
    proposal = {"review_id": record["review_id"], "reviewed_hash": shown["current_hash"],
                "old_tools": shown["metadata"]["current"].get("tools", []), "new_tools": tools}
    write(store / "catalogo-proposto.json", proposal)
    output(json.dumps(proposal, ensure_ascii=False, indent=2))
    if tools == proposal["old_tools"]:
        return {"status": "catalog_unchanged", "review_id": record["review_id"],
                "next": "O catálogo permanece igual; decida sobre a versão de código revisada."}
    output("Confira descrições e esquemas. Digite APLICAR_CATALOGO para alterar o manifesto; isso não aprova a versão:")
    if input_fn() != "APLICAR_CATALOGO":
        return {"status": "catalog_proposed", "proposal": str(store / "catalogo-proposto.json")}
    if digest(canon(capture(manifest))) != shown["current_hash"]:
        raise SentryError("estado mudou durante a descoberta/revisão do catálogo")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["metadata"]["tools"] = tools
    write(manifest, data)
    return {"status": "catalog_applied_review_required", "review": ensure_pending(manifest, store)[0]["review_id"],
            "next": "Revise o dossiê com código e catálogo e registre novo parecer antes de aceitar."}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Revisão e decisão local de atualização")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--store", type=Path)
    parser.add_argument("--state-root", type=Path, default=Path(os.environ.get("LOCALAPPDATA", Path.home())) / "MCP-Sentry")
    parser.add_argument("--action", choices=("once", "accept", "catalog", "envelope"), required=True)
    args = parser.parse_args(argv)
    try:
        if bool(args.manifest) != bool(args.store):
            raise SentryError("informe manifesto e store juntos")
        if args.manifest is None:
            choices = sorted(p for p in args.state_root.glob("*/config/manifest.json") if p.is_file())
            if not choices:
                raise SentryError("nenhum servidor preparado; informe --manifest e --store ou --state-root")
            for i, path in enumerate(choices, 1):
                print(f"{i}. {path.parent.parent.name}")
            selected = int(input("Servidor: "))
            if not 1 <= selected <= len(choices):
                raise SentryError("seleção inválida")
            args.manifest = choices[selected - 1]
            args.store = args.manifest.parent.parent / "state"
        print(json.dumps(decide(args.manifest, args.store, args.action), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, EOFError) as exc:
        print(f"mcp-sentry: blocked: {exc}")
        return 2
