@echo off
rem ARCHITECTURE - regenerate _tools\TYLER-TODAY.md from every project's
rem 00 Tasks\TYLER.md + the DECISION lane of each TASKS.md (ADR 0016).
rem Safe to run anytime; read-only except the digest file. Scheduled hourly
rem (Task Scheduler: "Atlas Tyler Digest"); double-click works too.
rem ATLAS_NO_PAUSE keeps a failed scheduled run from hanging on pause.
set ATLAS_NO_PAUSE=1
call "%~dp0Atlas.bat" tyler --drive "%~dp0.." --write
