#Requires -Version 7
param(
  [Parameter(Mandatory=$true)][string]$Authorization,
  [Parameter(Mandatory=$true)][string]$OutputRoot,
  [string]$Python = (Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw "Interpretador não encontrado: $Python" }
if ($env:OPENROUTER_API_KEY) { throw 'OPENROUTER_API_KEY já está no ambiente; limpe antes de iniciar.' }
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

# A credencial entra apenas no ambiente do processo filho: nunca em $env: do
# PowerShell, nunca na linha de comando e nunca ecoada.
$startInfo = [System.Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = $Python
$startInfo.WorkingDirectory = $repo
$startInfo.UseShellExecute = $false
foreach ($argument in @('-B', '-m', 'tools.m2_3_extensao_multimodelo_v1.campaign',
                        '--mode', 'campaign_real',
                        '--authorization', $Authorization,
                        '--output-root', $OutputRoot)) {
  $startInfo.ArgumentList.Add($argument)
}

$secureKey = Read-Host 'Cole a OPENROUTER_API_KEY e pressione Enter' -AsSecureString
$keyPointer = [IntPtr]::Zero
$process = $null
try {
  $keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
  $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
  if ([string]::IsNullOrWhiteSpace($plain)) { throw 'Chave vazia; campanha não iniciada.' }
  $startInfo.Environment['OPENROUTER_API_KEY'] = $plain
  $plain = $null
  $process = [System.Diagnostics.Process]::Start($startInfo)
  $startInfo.Environment.Remove('OPENROUTER_API_KEY') | Out-Null
  $process.WaitForExit()
  if ($process.ExitCode -ne 0) {
    throw "Campanha interrompida com código $($process.ExitCode). Não reinicie sem conferir os registros."
  }
}
finally {
  $startInfo.Environment.Remove('OPENROUTER_API_KEY') | Out-Null
  if ($keyPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer) }
  if ($null -ne $process) { $process.Dispose() }
  if ($null -ne $secureKey) { $secureKey.Dispose() }
  $plain = $null
  if ($env:OPENROUTER_API_KEY) { Remove-Item Env:\OPENROUTER_API_KEY }
}
