$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
& "$projectRoot\.venv\Scripts\python.exe" "$projectRoot\ferramentas-para-demonstracao\scripts-em-python\activate_demo_version.py" rug-pull --reset-session

