@echo off
@REM File: bin\rentals.cmd
@REM ------------------------------------------------------
@REM Summary:
@REM     Runs the Python module or package based on the script name.
@REM Usage:
@REM     rentals [ARGS...]
@REM Exit codes:
@REM     0 = Success
@REM     4 = Usage error or CLI method not found
@REM     5 = Internal or virtual environment error
@REM     Other = Script-specific error
@REM ------------------------------------------------------

setlocal enableextensions

@REM ------------------------------------------------------
@REM PROJECT_ROOT = Project root directory.
@REM SRC          = Subdirectory for source code.
@REM MODULE       = The Python module to run.
@REM ------------------------------------------------------

for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
set "SRC=src"
set "MODULE=mstair.%~n0"

@REM --------------------------------------
@REM ACTIVATE = Virtual environment activation script.
@REM --------------------------------------

set "ACTIVATE=%PROJECT_ROOT%\.venv\Scripts\activate.bat"
if not exist "%ACTIVATE%" (
    echo rentals: Virtual environment activation script not found in %PROJECT_ROOT%\.venv 1>&2
    exit /b 5
)

@REM Activate virtual environment
call "%ACTIVATE%"

@REM Raise an error if PYTHONPATH was not set by the activation script
if "%PYTHONPATH%"=="" (
    echo rentals: PYTHONPATH was not set by the virtual environment activation script 1>&2
    exit /b 5
)

@REM Run the Script
python -P -s -m "%MODULE%" %*
set "exitCode=%ERRORLEVEL%"
endlocal & exit /b %exitCode%
