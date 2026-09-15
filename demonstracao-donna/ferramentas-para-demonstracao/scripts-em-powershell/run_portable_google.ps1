param(
    [string]$Profile = "default",
    [string]$PortableHome = "",
    [string]$Timezone = "America/Sao_Paulo",
    [string]$CalendarId = "primary"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
. "$PSScriptRoot\portable_common.ps1"

$paths = Get-SecretaryPortablePaths -Profile $Profile -PortableHome $PortableHome
if (-not (Test-Path -LiteralPath $paths.Python -PathType Leaf)) {
    throw "Instalacao portátil ausente. Execute install_portable.ps1 primeiro."
}

Set-SecretaryPortableEnvironment -Paths $paths -Timezone $Timezone -CalendarId $CalendarId
& $paths.Python (Join-Path $projectRoot "inicializacao-do-mcp\server_google.py")
exit $LASTEXITCODE

