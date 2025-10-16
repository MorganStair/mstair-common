# File: scripts/Activate.ps1
#
# Minimal environment setup wrapper for PowerShell.

# Ensure we are in the project root and the virtual environment is set up
if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Error "This script must be run from the project root directory after setting up the virtual environment."
    return 1
}
# Ensure the original activation script exists
if (-not (Test-Path ".venv\Scripts\ActivateOriginal.ps1")) {
    Write-Error "1. Copy .venv\Scripts\Activate.ps1 to .venv\Scripts\ActivateOriginal.ps1"
    Write-Error "2. Copy this script to .venv\Scripts\Activate.ps1"
    Write-Error "3. Run .venv\Scripts\Activate.ps1 to activate the virtual environment with custom settings."
    return 1
}

# Set project directory
$env:PROJECT_DIR = (Get-Location).Path

# Set environment variables
$env:CACHE_DIR = "$env:PROJECT_DIR\.cache"
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
$env:JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION = "1"
$env:MYPY_CACHE_DIR = "$env:PROJECT_DIR\.cache\.mypy_cache"
$env:NODE_ENV = "development"
$env:PYDEVD_WARN_SLOW_RESOLVE_TIMEOUT = "5000"
$env:PYLINT_HOME = "$env:PROJECT_DIR\.cache\pylint"
$env:PYLINTRC = "$env:PROJECT_DIR\.pylintrc"
$env:PYTHONPYCACHEPREFIX = "$env:PROJECT_DIR\.cache\__pycache__"
$env:RUFF_CACHE_DIR = "$env:PROJECT_DIR\.cache\ruff"
$env:WITH_4BIT_QUANTIZATION = "1"

# Set PATH-like variables
$env:MYPYPATH = "$env:PROJECT_DIR\.cache\typings;$env:PROJECT_DIR\src"
$env:PATH = "$env:PROJECT_DIR\bin;$env:ProgramFiles\Git\usr\bin;$env:PATH"
$env:PYTHONPATH = "$env:PROJECT_DIR\src"

# Function to deduplicate PATH-like variables
function Dedupe-PathVar {
    param([string]$VarName)

    $origValue = (Get-Item "env:$VarName" -ErrorAction SilentlyContinue).Value
    if (-not $origValue) { return }

    $cleaned = @()
    $paths = $origValue -split ';'

    foreach ($path in $paths) {
        if ($path -and $cleaned -notcontains $path) {
            $cleaned += $path
        }
    }

    Set-Item "env:$VarName" -Value ($cleaned -join ';')
}

# Deduplicate PATH-like variables
Dedupe-PathVar "PATH"
Dedupe-PathVar "PYTHONPATH"
Dedupe-PathVar "MYPYPATH"

# Call the original activation script
. ".venv\Scripts\ActivateOriginal.ps1"

# Note: When dot-sourced, PowerShell will naturally propagate the exit code
