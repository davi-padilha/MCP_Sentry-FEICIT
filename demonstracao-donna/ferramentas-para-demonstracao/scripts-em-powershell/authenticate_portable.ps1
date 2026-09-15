param(
    [string]$CredentialsFile = "",
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

if ($CredentialsFile) {
    $source = [IO.Path]::GetFullPath($CredentialsFile)
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Credencial OAuth nao encontrada: $source"
    }
    if (Test-Path -LiteralPath $paths.Credentials) {
        $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash
        $targetHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $paths.Credentials).Hash
        if ($sourceHash -ne $targetHash) {
            throw "credentials.json ja existe com outro conteudo. Remova-o conscientemente antes de substituir."
        }
    } else {
        New-Item -ItemType Directory -Force -Path $paths.DataRoot | Out-Null
        Copy-Item -LiteralPath $source -Destination $paths.Credentials
    }
}

if (-not (Test-Path -LiteralPath $paths.Credentials -PathType Leaf)) {
    throw "Informe -CredentialsFile com o cliente OAuth Desktop baixado do Google Cloud."
}

Set-SecretaryPortableEnvironment -Paths $paths -Timezone $Timezone -CalendarId $CalendarId
& $paths.Python (Join-Path $projectRoot "ferramentas-para-demonstracao\scripts-em-python\authenticate_google.py")
if ($LASTEXITCODE -ne 0) { throw "Falha na autorizacao Google." }

Write-Host "OAuth concluido para o perfil '$Profile'."
Write-Host "Reinicie o cliente MCP e execute diagnose_portable.ps1 -CheckMcp."

