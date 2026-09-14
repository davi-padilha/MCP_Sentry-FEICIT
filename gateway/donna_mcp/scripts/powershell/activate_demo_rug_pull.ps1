$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
& "$projectRoot\.venv\Scripts\python.exe" "$projectRoot\scripts\python\activate_demo_version.py" rug-pull --reset-session
