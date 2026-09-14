$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
& "$projectRoot\.venv\Scripts\python.exe" "$projectRoot\entrypoints\server_aprovado.py"
