"""Painel local de auditoria para a apresentacao."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse

try:
    from ._bootstrap import configure_import_path
except ImportError:
    from _bootstrap import configure_import_path

configure_import_path()

from donna_mcp.audit import AuditLog  # noqa: E402
from donna_mcp.config import SecretaryConfig  # noqa: E402


HOST = "127.0.0.1"
PORT = 8765
CONFIG = SecretaryConfig.from_env()
AUDIT = AuditLog(CONFIG.audit_file)

HTML = r"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Donna MCP — Auditoria</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, system-ui, sans-serif; }
    body { margin: 0; background: #0b1020; color: #edf2ff; }
    header { padding: 28px 36px 18px; border-bottom: 1px solid #26314f; }
    h1 { margin: 0 0 8px; font-size: 28px; }
    p { margin: 0; color: #aebbd5; }
    main { padding: 24px 36px 40px; }
    .scenarios { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin-bottom: 20px; }
    .scenario { background: #141c31; border: 1px solid #26314f; border-radius: 12px; padding: 16px 18px; }
    .scenario .number { color: #9db5e6; font-size: 12px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
    .scenario h2 { font-size: 17px; margin: 6px 0 8px; }
    .scenario .state { color: #aebbd5; font-size: 14px; }
    .scenario.observed { border-color: #3d78e6; }
    .scenario.danger { background: #421923; border-color: #8e3547; }
    .scenario.danger .state { color: #ffb2bf; }
    .scenario.blocked { background: #183728; border-color: #2f855a; }
    .scenario.blocked .state { color: #9ae6b4; }
    .summary { display: flex; gap: 14px; margin-bottom: 20px; flex-wrap: wrap; }
    .metric { background: #141c31; border: 1px solid #26314f; border-radius: 12px; padding: 14px 18px; min-width: 150px; }
    .metric strong { display: block; font-size: 26px; }
    .metric span { color: #aebbd5; font-size: 13px; }
    button { background: #2f6fed; color: white; border: 0; padding: 10px 14px; border-radius: 8px; cursor: pointer; }
    table { width: 100%; border-collapse: collapse; background: #11182b; border-radius: 12px; overflow: hidden; }
    th, td { padding: 12px 14px; border-bottom: 1px solid #26314f; text-align: left; vertical-align: top; }
    th { color: #9db5e6; font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }
    td { font-size: 13px; }
    tr.hidden-action { background: #421923; }
    tr.hidden-action td:first-child { color: #ff8ca0; font-weight: 700; }
    tr.sentry-block { background: #3b2b12; }
    tr.sentry-block td:first-child { color: #ffd166; font-weight: 700; }
    code { color: #c9d8ff; white-space: pre-wrap; word-break: break-word; }
    .toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .badge { display: inline-block; padding: 3px 8px; border-radius: 999px; background: #22345b; }
    @media (max-width: 760px) {
      .scenarios { grid-template-columns: 1fr; }
      main, header { padding-left: 20px; padding-right: 20px; }
      table, tbody, tr, td { display: block; width: 100%; box-sizing: border-box; }
      thead { display: none; }
      tr { border-bottom: 1px solid #26314f; padding: 8px 0; }
      td { display: grid; grid-template-columns: 92px minmax(0, 1fr); gap: 10px; border: 0; padding: 7px 12px; }
      td::before { content: attr(data-label); color: #9db5e6; font-size: 11px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Donna MCP</h1>
    <p>Donna MCP — Assistente Local<br><small>Powered by MCP Sentry</small></p>
    <p>Painel local: ações legítimas e efeitos ocultos simulados aparecem em trilhas separadas.</p>
  </header>
  <main>
    <section class="scenarios" aria-label="Resultados dos três cenários">
      <article class="scenario" id="scenario-approved">
        <span class="number">Cenário 1</span>
        <h2>Versão aprovada</h2>
        <div class="state">Aguardando fluxo normal</div>
      </article>
      <article class="scenario" id="scenario-rug-pull">
        <span class="number">Cenário 2</span>
        <h2>Rug pull sem proteção</h2>
        <div class="state">Aguardando ação oculta</div>
      </article>
      <article class="scenario" id="scenario-sentry">
        <span class="number">Cenário 3</span>
        <h2>Rug pull com Sentry</h2>
        <div class="state">Aguardando bloqueio</div>
      </article>
    </section>
    <section class="summary">
      <div class="metric"><strong id="total">0</strong><span>ações registradas</span></div>
      <div class="metric"><strong id="hidden">0</strong><span>ações ocultas simuladas</span></div>
      <div class="metric"><strong id="blocked">0</strong><span>bloqueios do Sentry</span></div>
      <div class="metric"><strong id="network">0</strong><span>ações de rede no ataque</span></div>
    </section>
    <div class="toolbar">
      <span class="badge">Atualização automática</span>
      <button id="clear">Limpar painel</button>
    </div>
    <table>
      <thead><tr><th>Tipo</th><th>Horário UTC</th><th>Detalhes</th></tr></thead>
      <tbody id="events"></tbody>
    </table>
  </main>
  <script>
    function escapeHtml(value) {
      return String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
    }
    async function refresh() {
      const response = await fetch('/api/audit', {cache: 'no-store'});
      const events = await response.json();
      const hidden = events.filter(event => event.event_type === 'simulated_hidden_action');
      const blocked = events.filter(event => event.event_type === 'sentry_decision' && !event.permitir);
      const approved = events.filter(event => event.provider === 'simulated-approved-active');
      setScenario('#scenario-approved', approved.length > 0, 'Fluxo normal observado', 'Aguardando fluxo normal', 'observed');
      setScenario('#scenario-rug-pull', hidden.length > 0, 'Ação oculta simulada observada', 'Aguardando ação oculta', 'danger');
      setScenario('#scenario-sentry', blocked.length > 0, 'Alteração bloqueada antes do efeito', 'Aguardando bloqueio', 'blocked');
      document.querySelector('#total').textContent = events.length;
      document.querySelector('#hidden').textContent = hidden.length;
      document.querySelector('#blocked').textContent = blocked.length;
      document.querySelector('#network').textContent = hidden.filter(event => event.network_performed).length;
      document.querySelector('#events').innerHTML = events.slice().reverse().map(event => {
        const details = {...event}; delete details.event_type; delete details.timestamp;
        const rowClass = event.event_type === 'simulated_hidden_action'
          ? 'hidden-action'
          : (event.event_type === 'sentry_decision' && !event.permitir ? 'sentry-block' : '');
        return `<tr class="${rowClass}"><td data-label="Tipo">${escapeHtml(event.event_type)}</td><td data-label="Horário UTC">${escapeHtml(event.timestamp)}</td><td data-label="Detalhes"><code>${escapeHtml(JSON.stringify(details, null, 2))}</code></td></tr>`;
      }).join('');
    }
    function setScenario(selector, complete, completedText, pendingText, stateClass) {
      const card = document.querySelector(selector);
      card.classList.toggle(stateClass, complete);
      card.querySelector('.state').textContent = complete ? completedText : pendingText;
    }
    document.querySelector('#clear').addEventListener('click', async () => {
      await fetch('/api/audit', {method: 'DELETE'}); await refresh();
    });
    refresh(); setInterval(refresh, 1500);
  </script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            self._send("text/html; charset=utf-8", HTML.encode("utf-8"))
            return
        if path == "/api/audit":
            payload = json.dumps(AUDIT.read_all(), ensure_ascii=False).encode("utf-8")
            self._send("application/json; charset=utf-8", payload)
            return
        self.send_error(404)

    def do_DELETE(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/audit":
            self.send_error(404)
            return
        AUDIT.clear()
        self._send("application/json", b'{"status":"cleared"}')

    def _send(self, content_type: str, payload: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), DashboardHandler)
    print(f"Painel disponivel em http://{HOST}:{PORT}")
    print(f"Lendo auditoria de: {CONFIG.audit_file}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
