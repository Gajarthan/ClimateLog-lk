param(
    [Parameter(Mandatory = $true)][string]$DataDirectory,
    [Parameter(Mandatory = $true)][datetime]$At,
    [string]$TaskName = 'WeatherPipeline'
)

# Run explicitly after validating collection and configuring backup retention.
$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectDirectory '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Install the project in .venv first.' }
if (-not [IO.Path]::IsPathRooted($DataDirectory)) { throw 'DataDirectory must be absolute.' }
if ($DataDirectory.Contains('"')) { throw 'DataDirectory cannot contain quotes.' }
$arguments = '-m weather_lk --data-dir "{0}" run' -f $DataDirectory
$action = New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $projectDirectory
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 15)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description 'Collect, validate, and export weather reports from durable local storage'
