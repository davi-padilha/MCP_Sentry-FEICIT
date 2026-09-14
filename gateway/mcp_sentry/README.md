# MCP Sentry Gateway

Gateway local que verifica código, configuração e metadados antes de iniciar
um servidor MCP protegido.

- `gateway/`: pacote Python instalável;
- `tests/`: suíte local;
- `examples/`: servidor MCP mínimo;
- `demonstracoes/`: manifesto da integração Donna;
- `docs/`: documentos essenciais do MVP, T7 e FEICIT.

Instalação, comandos e limitações estão em `gateway/README.md`.

Para executar os testes a partir desta pasta:

```powershell
$env:PYTHONPATH = "gateway\src"
python -m unittest discover -s tests -v
```

