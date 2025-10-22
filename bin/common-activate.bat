@echo off
rem Minimal environment setup wrapper for Windows batch.

rem Set project directory
set "PROJECT_DIR=%CD%"

rem Set environment variables
set "CACHE_DIR=%PROJECT_DIR%\.cache"
set HF_HUB_DISABLE_SYMLINKS_WARNING=1
set JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1
set "MYPY_CACHE_DIR=%PROJECT_DIR%\.cache\.mypy_cache"
set NODE_ENV=development
set PYDEVD_WARN_SLOW_RESOLVE_TIMEOUT=5000
set "PYLINT_HOME=%PROJECT_DIR%\.cache\pylint"
set "PYLINTRC=%PROJECT_DIR%\.pylintrc"
set "PYTHONPYCACHEPREFIX=%PROJECT_DIR%\.cache\__pycache__"
set "RUFF_CACHE_DIR=%PROJECT_DIR%\.cache\ruff"
set WITH_4BIT_QUANTIZATION=1

rem Set PATH-like variables
if not defined MYPYPATH set MYPYPATH=
if not defined PYTHONPATH set PYTHONPATH=
set "MYPYPATH=%PROJECT_DIR%\.cache\typings;%PROJECT_DIR%\src"
set "PATH=%PROJECT_DIR%\bin;%ProgramFiles%\Git\usr\bin;%PATH%"
set "PYTHONPATH=%PROJECT_DIR%\src"

rem Deduplicate PATH-like variables
call :dedupe_path_var PATH

rem Call the original activation script
call ".venv\Scripts\activate.bat"

rem Return control to caller with the same errorlevel
exit /b %ERRORLEVEL%

REM --------------------------------------
REM Function: dedupe_path_var
REM Deduplicate a PATH-like variable in place.
REM Usage: call :dedupe_path_var VAR_NAME
REM --------------------------------------
:dedupe_path_var
setlocal enabledelayedexpansion
set "VAR_NAME=%~1"
call set "ORIG=%%%VAR_NAME%%%"
if not defined ORIG endlocal & goto :eof
set "CLEANED="
for %%P in ("%ORIG:;=" "%") do (
    rem Skip empty elements
    if not "%%~P"=="" (
        set "DUP="
        for %%C in (!CLEANED!) do (
            if /I "%%~P"=="%%~C" set "DUP=1"
        )
        if not defined DUP (
            if defined CLEANED (
                set "CLEANED=!CLEANED!;%%~P"
            ) else (
                set "CLEANED=%%~P"
            )
        )
    )
)
endlocal & set "%VAR_NAME%=%CLEANED%"
goto :eof
