$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Assert-SecretaryPortableProfile {
    param([Parameter(Mandatory = $true)][string]$Profile)

    if ($Profile -notmatch '^[A-Za-z0-9_-]+$') {
        throw "Profile invalido. Use somente letras, numeros, '_' e '-'."
    }
}

function Get-SecretaryPortablePaths {
    param(
        [string]$Profile = "default",
        [string]$PortableHome = ""
    )

    Assert-SecretaryPortableProfile -Profile $Profile

    if (-not $PortableHome) {
        $PortableHome = $env:MCP_SECRETARY_PORTABLE_HOME
    }
    if (-not $PortableHome) {
        $localAppData = [Environment]::GetFolderPath(
            [Environment+SpecialFolder]::LocalApplicationData
        )
        if (-not $localAppData) {
            throw "LOCALAPPDATA nao encontrado. Informe -PortableHome."
        }
        $PortableHome = Join-Path $localAppData "DonnaMCP"
    }

    $portableRoot = [IO.Path]::GetFullPath($PortableHome)
    $profileRoot = Join-Path $portableRoot $Profile
    $dataRoot = Join-Path $profileRoot "data"
    $venvRoot = Join-Path $profileRoot "venv"
    # O diretorio de dados preserva o nome historico para manter tokens OAuth
    # locais existentes durante a migracao de identidade para Donna MCP.
    $serverName = if ($Profile -eq "default") {
        "donna_mcp"
    } else {
        "donna_mcp_$Profile"
    }

    [pscustomobject]@{
        Profile = $Profile
        ServerName = $serverName
        PortableRoot = $portableRoot
        ProfileRoot = $profileRoot
        DataRoot = $dataRoot
        VenvRoot = $venvRoot
        Python = Join-Path $venvRoot "Scripts\python.exe"
        Credentials = Join-Path $dataRoot "credentials.json"
        Token = Join-Path $dataRoot "token.json"
        Audit = Join-Path $dataRoot "audit.jsonl"
        Mutations = Join-Path $dataRoot "mutations.json"
        CodexSnippet = Join-Path $profileRoot "codex_config.toml"
        ClientManifest = Join-Path $profileRoot "stdio_connection.json"
    }
}

function Resolve-SecretaryBootstrapPython {
    param([string]$PythonExecutable = "")

    if ($PythonExecutable) {
        $resolved = [IO.Path]::GetFullPath($PythonExecutable)
        if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
            throw "Python nao encontrado: $resolved"
        }
        return $resolved
    }

    $bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if (Test-Path -LiteralPath $bundledPython -PathType Leaf) {
        return $bundledPython
    }

    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return $pythonCommand.Source
    }

    $pyLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        $candidate = (& $pyLauncher.Source -3 -c "import sys; print(sys.executable)").Trim()
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return $candidate
        }
    }

    throw "Python 3.10+ nao encontrado. Instale Python ou informe -PythonExecutable."
}

function Set-SecretaryPortableEnvironment {
    param(
        [Parameter(Mandatory = $true)]$Paths,
        [string]$Timezone = "America/Sao_Paulo",
        [string]$CalendarId = "primary"
    )

    $env:MCP_SECRETARY_MODE = "live-google"
    $env:MCP_SECRETARY_TIMEZONE = $Timezone
    $env:MCP_SECRETARY_CALENDAR_ID = $CalendarId
    $env:MCP_SECRETARY_CREDENTIALS_FILE = $Paths.Credentials
    $env:MCP_SECRETARY_TOKEN_FILE = $Paths.Token
    $env:MCP_SECRETARY_AUDIT_FILE = $Paths.Audit
    $env:MCP_SECRETARY_MUTATION_STORE_FILE = $Paths.Mutations
    # A protecao atual cobre somente o provedor simulado ativo. Nao sugerir
    # protecao inexistente no modo Google real.
}
