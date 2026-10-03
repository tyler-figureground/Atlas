@echo off
rem ARCHITECTURE - preview what conform would change on every project (dry run, safe).
rem Missing template files, seeded folders, renames, relocations. Nothing is written.
call "%~dp0Atlas.bat" conform --all
