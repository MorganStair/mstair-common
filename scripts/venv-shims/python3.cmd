@echo off
REM Simple shim so "python3" invokes the venv's Python on Windows.
REM Usage: python3 [args...]
"%~dp0python.exe" %*
