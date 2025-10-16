@echo off
@REM File: tools\bin\pys.cmd
@REM ---------------------------------------------------
@REM Summary:
@REM     Run a Python CLI from the modules in the current project.
@REM Usage:
@REM     pys TOOL [ARGS...]
@REM Exit codes:
@REM     0 = Success
@REM     2 = Usage error or CLI method not found
@REM     3 = Internal or virtual environment error
@REM     Other = Script-specific error
@REM ---------------------------------------------------


@REM ----------------------------------------------------
@REM Initial Setup and Usage Check:
@REM ECHO_OUTER = The original echo state before running this script.
@REM ECHO_INNER = The echo state while running this script.
@REM ----------------------------------------------------

@setlocal enableextensions enabledelayedexpansion
@for /f "tokens=2 delims=[]" %%A in ('echo.^| "%SystemRoot%\System32\find.exe" /I "ECHO"') do set "ECHO_OUTER=%%A"
@set "ECHO_INNER=off"
@echo %ECHO_INNER% >nul
if "%~1"=="" (
  echo Usage: pys TOOL [ARGS...] 1>&2
  exit /b 2
)
REM ----------------------------------------------------
REM Script CLI Existence Check:
REM PROJECT_ROOT = The root directory of the project (one level up from this script).
REM SRC          = The project subdirectory for the source code ("src").
REM TOOL         = The name of the tool to run (first argument).
REM ----------------------------------------------------

for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
set "SRC=src"
set "TOOL=%~n1"

REM ----------------------------------------------------
REM Virtual Environment Activation:
REM ACTIVATE = The script to activate the virtual environment.
REM ----------------------------------------------------

set "ACTIVATE=%PROJECT_ROOT%\.venv\Scripts\activate.bat"
if not exist "%ACTIVATE%" (
  echo [ERROR] Missing virtual environment at "%PROJECT_ROOT%\.venv". 1>&2
  endlocal & exit /b 3
)
echo %ECHO_INNER% >nul
call "%ACTIVATE%" >nul 2>&1
@echo %ECHO_INNER% >nul

REM ----------------------------------------------------
REM Run the Script:
REM ARGS = The Script Arguments
REM ----------------------------------------------------

call :parse_args ARGS 1 %*
REM -P = Prevent prepending unsafe paths to sys.path.
REM -s = Disable user site directory.
call python -P -s -m "%TOOL%" %ARGS%
set "exitCode=%ERRORLEVEL%"
call deactivate >nul 2>&1
endlocal & @echo %ECHO_OUTER% >nul & exit /b %exitCode%

REM ----------------------------------------------------
REM Helper function: parse_args
REM ----------------------------------------------------
REM Skip the first SKIP arguments.
REM Usage: call :parse_args VARNAME SKIP %*
REM Sets variable named VARNAME to the remaining arguments.
REM ----------------------------------------------------
:parse_args
setlocal enabledelayedexpansion
set "VARNAME=%~1"
set /a SKIP=%~2
shift & shift

:parse_args_skip
if !SKIP! gtr 0 (
    set /a SKIP-=1
    shift
    goto :parse_args_skip
)

set "RESULT="

:parse_args_loop
if "%~1"=="" (
    endlocal & set "%VARNAME%=%RESULT%" & exit /b
)
if not defined RESULT (
    set "RESULT="%~1""
) else (
    set "RESULT=!RESULT! "%~1""
)
shift
goto :parse_args_loop
