@echo off
rem ARCHITECTURE - zip agent runs idle 14 days into each project's .agent\archive\.
rem A run named in 00 Tasks or .agent\handoff stays open. Each zip is read back and
rem checked before its folder is removed. Preview only: Archive-Agent-Runs.bat --preview
if /i "%~1"=="--preview" (
  call "%~dp0Atlas.bat" runs --all
) else (
  call "%~dp0Atlas.bat" runs --all --apply
)
