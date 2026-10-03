<# :
@echo off
rem ARCHITECTURE - set up right-click dated folders on this PC. Run once per PC.
rem Installs PowerToys if missing, turns on New+ and its date variables, and
rem points New+ at _tools\New+ Templates (found next to this file, whatever
rem drive letter Google Drive uses here). Safe to run again.
rem Source: skills-for-architects\tools\atlas\launchers\Setup-New-Plus.bat
rem The PowerShell below the batch part does the work.
set "NP_TEMPLATES=%~dp0New+ Templates"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-Expression ([IO.File]::ReadAllText('%~f0'))"
if errorlevel 1 (
  echo.
  echo Setup did not finish - see the message above.
)
pause
exit /b
#>

$ErrorActionPreference = 'Stop'
$templates = $env:NP_TEMPLATES
if (-not (Test-Path -LiteralPath $templates)) {
  Write-Host "Templates folder not found: $templates"
  Write-Host 'Run this file from _tools on the ARCHITECTURE drive.'
  exit 1
}

function Find-PowerToys {
  foreach ($p in "$env:LOCALAPPDATA\PowerToys\PowerToys.exe", "$env:ProgramFiles\PowerToys\PowerToys.exe") {
    if (Test-Path -LiteralPath $p) { return $p }
  }
}

$exe = Find-PowerToys
if (-not $exe) {
  Write-Host 'Installing PowerToys (one time, a few minutes)...'
  winget install --id Microsoft.PowerToys --scope user --silent --accept-package-agreements --accept-source-agreements
  $exe = Find-PowerToys
  if (-not $exe) { Write-Host 'PowerToys did not install. Install it from the Microsoft Store, then run this again.'; exit 1 }
}

# PowerToys writes its settings on first start; wait for them, then stop it so
# it cannot overwrite the edits below.
$root = "$env:LOCALAPPDATA\Microsoft\PowerToys"
$general = "$root\settings.json"
if (-not (Test-Path -LiteralPath $general)) {
  Write-Host 'Starting PowerToys once to create its settings...'
  Start-Process $exe
  $deadline = (Get-Date).AddSeconds(60)
  while (-not (Test-Path -LiteralPath $general) -and (Get-Date) -lt $deadline) { Start-Sleep 1 }
  if (-not (Test-Path -LiteralPath $general)) { Write-Host 'PowerToys never wrote its settings. Open PowerToys once, then run this again.'; exit 1 }
  Start-Sleep 3
}
Get-Process PowerToys* -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 2

$utf8 = New-Object Text.UTF8Encoding $false
function Read-Json($path) { ([IO.File]::ReadAllText($path)).TrimStart([char]0xFEFF) | ConvertFrom-Json }
function Write-Json($path, $obj) { [IO.File]::WriteAllText($path, ($obj | ConvertTo-Json -Depth 10 -Compress), $utf8) }

$g = Read-Json $general
if ($g.enabled.PSObject.Properties['NewPlus']) { $g.enabled.NewPlus = $true }
else { $g.enabled | Add-Member -NotePropertyName NewPlus -NotePropertyValue $true }
Write-Json $general $g

$npDir = "$root\NewPlus"
$npFile = "$npDir\settings.json"
New-Item -ItemType Directory -Force -Path $npDir | Out-Null
if (Test-Path -LiteralPath $npFile) { $n = Read-Json $npFile }
else { $n = [pscustomobject]@{ version = '1.0'; name = 'NewPlus'; properties = [pscustomobject]@{} } }
$want = [ordered]@{ HideFileExtension = $true; HideStartingDigits = $true; ReplaceVariables = $true; TemplateLocation = $templates }
foreach ($k in $want.Keys) {
  if ($n.properties.PSObject.Properties[$k] -and $k -in 'HideFileExtension', 'HideStartingDigits') { continue }
  $n.properties | Add-Member -Force -NotePropertyName $k -NotePropertyValue ([pscustomobject]@{ value = $want[$k] })
}
Write-Json $npFile $n

Start-Process $exe
Write-Host ''
Write-Host 'Done. New+ is on and reads templates from:'
Write-Host "  $templates"
Write-Host ''
Write-Host 'Try it: right-click inside any folder -> New+ -> YYMMDD_Site Visit.'
Write-Host 'Press End before typing so the date stays.'
