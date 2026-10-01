# Desenvolvimento do gateway atual

Código-fonte da candidata 0.8.0. O usuário recebe somente a pasta
[pacote-usuario/](../../pacote-usuario/README.md), com o wheel e seu manual.
O protótipo antigo está em [prototipo-feicit/](../../prototipo-feicit/README.md).

Na raiz do repositório, em PowerShell:

```powershell
python -m venv .\desenvolvimento\gateway\.venv
& .\desenvolvimento\gateway\.venv\Scripts\python.exe -m pip install .\desenvolvimento\gateway
& .\desenvolvimento\gateway\.venv\Scripts\python.exe -m unittest discover -s desenvolvimento/gateway/testes -q
```

Para gerar uma distribuição nova, instale a ferramenta de build no ambiente de
desenvolvimento e execute `python -m build --wheel --outdir ../../pacote-usuario`
nesta pasta. Ambientes virtuais, testes e arquivos intermediários não fazem
parte da entrega ao usuário.

[Guia do piloto](../../documentacao/GUIA_PILOTO.md).
