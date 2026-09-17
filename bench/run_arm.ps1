param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$WorkDir,
    [Parameter(Mandatory = $true)][string]$PromptFile,
    [string]$PluginDir = "",
    [string]$Model = "fable"
)
# Runs one benchmark arm headlessly and records its session id and JSON result next to this script.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$sid = [guid]::NewGuid().ToString()
Set-Content -Path (Join-Path $here "$Name.sid") -Value $sid -Encoding ascii
$prompt = (Get-Content -Raw -Path $PromptFile).Trim()
$cliArgs = @("-p", $prompt, "--model", $Model, "--session-id", $sid, "--output-format", "json",
    "--permission-mode", "acceptEdits",
    "--allowedTools", "Bash(python *)", "Bash(python:*)", "PowerShell(python *)", "PowerShell(python:*)")
if ($PluginDir) { $cliArgs += @("--plugin-dir", $PluginDir) }
Push-Location $WorkDir
try { & claude @cliArgs > (Join-Path $here "$Name.json") } finally { Pop-Location }
"done $Name exit=$LASTEXITCODE session=$sid"
