@echo off
rem Atlas - studio drive + project tooling. Double-click to open the console.
rem Every other .bat in _tools calls this one, so this is the only version pin.
rem Upgrading = drop the new wheel in _tools\atlas\ and update the WHEEL line.
rem Source: skills-for-architects\tools\atlas\launchers\Atlas.bat
set "WHEEL=%~dp0atlas\studio_atlas-0.9.2-py3-none-any.whl"

where uv >nul 2>nul
if errorlevel 1 (
  echo Atlas needs uv - installing it once via winget...
  winget install --id=astral-sh.uv -e --silent
  if errorlevel 1 (
    echo.
    echo Could not install uv automatically.
    echo Install it from https://docs.astral.sh/uv/ then double-click Atlas.bat again.
    pause
    exit /b 1
  )
)

uv tool run --from "%WHEEL%" atlas %*
if errorlevel 1 pause
