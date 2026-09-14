param(
    [string]$PythonExecutable = "",
    [string]$Profile = "default",
    [string]$PortableHome = "",
    [string]$CodexConfigPath = "",
    [string]$Timezone = "America/Sao_Paulo",
    [string]$CalendarId = "primary",
    [string]$CredentialsFile = "",
    [switch]$SkipTests,
    [switch]$SkipCodexRegistration
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
. "$PSScriptRoot\portable_common.ps1"

$paths = Get-SecretaryPortablePaths -Profile $Profile -PortableHome $PortableHome
$bootstrapPython = Resolve-SecretaryBootstrapPython -PythonExecutable $PythonExecutable
$server = Join-Path $projectRoot "entrypoints\server_google.py"
$configTool = Join-Path $projectRoot "scripts\python\portable_config.py"

& $bootstrapPython -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "Donna MCP requer Python 3.10 ou superior."
}

New-Item -ItemType Directory -Force -Path $paths.ProfileRoot, $paths.DataRoot | Out-Null
if (-not (Test-Path -LiteralPath $paths.Python -PathType Leaf)) {
    & $bootstrapPython -m venv $paths.VenvRoot
    if ($LASTEXITCODE -ne 0) { throw "Falha ao criar o ambiente virtual portátil." }
}

& $paths.Python -m pip install --disable-pip-version-check --quiet -r (Join-Path $projectRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependencias fixadas." }
& $paths.Python -m pip install --disable-pip-version-check --quiet --no-deps -e $projectRoot
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar o pacote Donna MCP." }
$gatewayRoot = Join-Path (Split-Path -Parent $projectRoot) "codigo_gateway"
& $paths.Python -m pip install --disable-pip-version-check --quiet --no-deps -e $gatewayRoot
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar o pacote MCP Sentry Gateway." }
& $paths.Python -m pip check
if ($LASTEXITCODE -ne 0) { throw "O ambiente portátil possui dependencias quebradas." }

if ($CredentialsFile) {
    $credentialSource = [IO.Path]::GetFullPath($CredentialsFile)
    if (-not (Test-Path -LiteralPath $credentialSource -PathType Leaf)) {
        throw "Credencial OAuth nao encontrada: $credentialSource"
    }
    if (Test-Path -LiteralPath $paths.Credentials) {
        $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $credentialSource).Hash
        $targetHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $paths.Credentials).Hash
        if ($sourceHash -ne $targetHash) {
            throw "credentials.json ja existe com outro conteudo. Remova-o conscientemente antes de substituir."
        }
    } else {
        Copy-Item -LiteralPath $credentialSource -Destination $paths.Credentials
    }
}

if (-not $SkipTests) {
    Push-Location $projectRoot
    try {
        & $paths.Python -m unittest discover -s tests -v
        if ($LASTEXITCODE -ne 0) { throw "Falha nos testes unitarios." }
        & $paths.Python scripts\python\verify_mcp.py
        if ($LASTEXITCODE -ne 0) { throw "Falha na verificacao MCP por stdio." }
    } finally {
        Pop-Location
    }
}

$configArgs = @(
    "--profile", $Profile,
    "--python", $paths.Python,
    "--server", $server,
    "--cwd", $projectRoot,
    "--timezone", $Timezone,
    "--calendar-id", $CalendarId,
    "--credentials", $paths.Credentials,
    "--token", $paths.Token,
    "--audit", $paths.Audit,
    "--mutations", $paths.Mutations
)

& $paths.Python $configTool render @configArgs --output $paths.CodexSnippet
if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar o trecho de configuracao do Codex." }
& $paths.Python $configTool render-client @configArgs --output $paths.ClientManifest
if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar o manifesto stdio genérico." }

if (-not $SkipCodexRegistration) {
    if (-not $CodexConfigPath) {
        $CodexConfigPath = Join-Path $env:USERPROFILE ".codex\config.toml"
    }
    & $paths.Python $configTool register @configArgs --config $CodexConfigPath
    if ($LASTEXITCODE -ne 0) { throw "Falha ao registrar Donna MCP no Codex." }
}

Write-Host "Donna MCP portátil instalado para o perfil '$Profile'."
Write-Host "Dados locais: $($paths.DataRoot)"
Write-Host "Trecho Codex: $($paths.CodexSnippet)"
Write-Host "Manifesto stdio: $($paths.ClientManifest)"
if (-not (Test-Path -LiteralPath $paths.Credentials)) {
    Write-Host "Proximo passo: execute authenticate_portable.ps1 -CredentialsFile <client_secret.json>."
} elseif (-not (Test-Path -LiteralPath $paths.Token)) {
    Write-Host "Proximo passo: execute authenticate_portable.ps1 para autorizar o Google."
} else {
    Write-Host "OAuth ja presente. Reinicie o Codex e execute diagnose_portable.ps1 -CheckMcp."
}
