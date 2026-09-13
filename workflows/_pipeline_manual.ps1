param(
    [string]$DataDirectory = $env:WEATHER_DATA_DIR,
    [string[]]$Files = @(),
    [switch]$NoCharts
)

$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
if (-not $DataDirectory) { $DataDirectory = Join-Path $projectDirectory 'var/weather_lk' }
$python = Join-Path $projectDirectory '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }
$arguments = @('-m', 'weather_lk', '--data-dir', $DataDirectory, 'run')
foreach ($file in $Files) { $arguments += @('--file', $file) }
if ($NoCharts) { $arguments += '--no-charts' }
& $python @arguments
exit $LASTEXITCODE
