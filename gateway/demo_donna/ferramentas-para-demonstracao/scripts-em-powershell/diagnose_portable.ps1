param(
    [string]$Profile = "default",
    [string]$PortableHome = "",
    [string]$CodexConfigPath = "",
    [string]$Timezone = "America/Sao_Paulo",
    [string]$CalendarId = "primary",
    [switch]$CheckMcp
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
. "$PSScriptRoot\portable_common.ps1"

$paths = Get-SecretaryPortablePaths -Profile $Profile -PortableHome $PortableHome
if (-not $CodexConfigPath) {
    $CodexConfigPath = Join-Path $env:USERPROFILE ".codex\config.toml"
}

$summary = [ordered]@{
    Profile = $Profile
    ServerName = $paths.ServerName
    Python = Test-Path -LiteralPath $paths.Python -PathType Leaf
    Credentials = Test-Path -LiteralPath $paths.Credentials -PathType Leaf
    Token = Test-Path -LiteralPath $paths.Token -PathType Leaf
    CodexConfig = Test-Path -LiteralPath $CodexConfigPath -PathType Leaf
    CodexRegistered = $false
    McpStartup = if ($CheckMcp) { "pending" } else { "not-requested" }
}

if ($summary.Python) {
    & $paths.Python -m pip check
    if ($LASTEXITCODE -ne 0) { throw "Dependencias quebradas no ambiente portátil." }
    $configArgs = @(
        "--profile", $Profile,
        "--python", $paths.Python,
        "--server", (Join-Path $projectRoot "inicializacao-do-mcp\server_google.py"),
        "--cwd", $projectRoot,
        "--timezone", $Timezone,
        "--calendar-id", $CalendarId,
        "--credentials", $paths.Credentials,
        "--token", $paths.Token,
        "--audit", $paths.Audit,
        "--mutations", $paths.Mutations,
        "--config", $CodexConfigPath
    )
    $checkJson = & $paths.Python (Join-Path $projectRoot "ferramentas-para-demonstracao\scripts-em-python\portable_config.py") check @configArgs
    if ($LASTEXITCODE -ne 0) { throw "Falha ao inspecionar a configuracao Codex." }
    $summary.CodexRegistered = [bool](($checkJson | ConvertFrom-Json).registered)
}

if ($CheckMcp) {
    if (-not $summary.Python -or -not $summary.Credentials -or -not $summary.Token) {
        throw "O handshake MCP exige instalacao, credentials.json e token.json."
    }
    Set-SecretaryPortableEnvironment -Paths $paths -Timezone $Timezone -CalendarId $CalendarId
    & $paths.Python (Join-Path $projectRoot "ferramentas-para-demonstracao\scripts-em-python\verify_live_mcp.py")
    if ($LASTEXITCODE -ne 0) { throw "Falha no startup do MCP Google." }
    $summary.McpStartup = "ok"
}

[pscustomobject]$summary | Format-List

if (-not $summary.Python) { exit 2 }
if (-not $summary.Credentials -or -not $summary.Token) { exit 3 }
if (-not $summary.CodexRegistered) { exit 4 }

