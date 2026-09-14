param([string]$PythonExecutable = "")

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$venvPath = Join-Path $projectRoot ".venv"
Push-Location $projectRoot

try {
if (-not $PythonExecutable) {
    $bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if (Test-Path -LiteralPath $bundledPython) {
        $PythonExecutable = $bundledPython
    } else {
        $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($pythonCommand) {
            $PythonExecutable = $pythonCommand.Source
        }
    }
}

if (-not $PythonExecutable -or -not (Test-Path -LiteralPath $PythonExecutable)) {
    throw "Python nao encontrado. Execute .\setup.ps1 -PythonExecutable 'C:\caminho\python.exe'."
}

& $PythonExecutable -m venv $venvPath
if ($LASTEXITCODE -ne 0) { throw "Falha ao criar o ambiente virtual." }

& "$venvPath\Scripts\python.exe" -m pip install -r "$projectRoot\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependencias." }

# Os entrypoints sao executados pelo interpretador do ambiente. Instalar os
# dois projetos locais nele evita depender de PYTHONPATH, do diretorio atual ou
# de aliases Windows durante a demonstracao via stdio.
& "$venvPath\Scripts\python.exe" -m pip install --no-deps -e "$projectRoot"
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar o pacote Donna MCP." }
$gatewayRoot = Join-Path (Split-Path -Parent $projectRoot) "codigo_gateway"
& "$venvPath\Scripts\python.exe" -m pip install --no-deps -e "$gatewayRoot"
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar o pacote MCP Sentry Gateway." }

& "$venvPath\Scripts\python.exe" -m unittest discover -s "$projectRoot\tests" -v
if ($LASTEXITCODE -ne 0) { throw "Falha nos testes unitarios." }

& "$venvPath\Scripts\python.exe" "$projectRoot\scripts\python\verify_mcp.py"
if ($LASTEXITCODE -ne 0) { throw "Falha na verificacao MCP por stdio." }

& "$venvPath\Scripts\python.exe" "$projectRoot\scripts\python\compare_versions.py"
if ($LASTEXITCODE -ne 0) { throw "Falha na comparacao das versoes." }

& "$venvPath\Scripts\python.exe" "$projectRoot\scripts\python\activate_demo_version.py" approved --reset-session --clear-audit
if ($LASTEXITCODE -ne 0) { throw "Falha ao ativar a versao aprovada." }

Write-Host "Donna MCP preparado e verificado."
} finally {
    Pop-Location
}
