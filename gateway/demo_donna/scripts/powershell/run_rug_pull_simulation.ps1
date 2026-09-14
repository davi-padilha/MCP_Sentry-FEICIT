$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
& "$projectRoot\.venv\Scripts\python.exe" "$projectRoot\entrypoints\server_rug_pull_simulado.py"
