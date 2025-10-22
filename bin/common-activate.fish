# Minimal environment setup wrapper for fish shell.

# Set project directory
set -gx PROJECT_DIR (pwd)

# Set environment variables
set -gx CACHE_DIR "$PROJECT_DIR/.cache"
set -gx HF_HUB_DISABLE_SYMLINKS_WARNING "1"
set -gx JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION "1"
set -gx MYPY_CACHE_DIR "$PROJECT_DIR/.cache/.mypy_cache"
set -gx NODE_ENV "development"
set -gx PYDEVD_WARN_SLOW_RESOLVE_TIMEOUT "5000"
set -gx PYLINT_HOME "$PROJECT_DIR/.cache/pylint"
set -gx PYLINTRC "$PROJECT_DIR/.pylintrc"
set -gx PYTHONPYCACHEPREFIX "$PROJECT_DIR/.cache/__pycache__"
set -gx RUFF_CACHE_DIR "$PROJECT_DIR/.cache/ruff"
set -gx WITH_4BIT_QUANTIZATION "1"

# Set PATH-like variables
set -gx MYPYPATH "$PROJECT_DIR/.cache/typings:$PROJECT_DIR/src"
set -gx PATH "$PROJECT_DIR/bin" "/c/Program Files/Git/usr/bin" $PATH
set -gx PYTHONPATH "$PROJECT_DIR/src"

# Function to deduplicate PATH-like variables
function dedupe_path_var
    set var_name $argv[1]
    set orig_value $$var_name
    if test -z "$orig_value"
        return
    end

    set cleaned ""
    set path_array (string split ":" "$orig_value")

    for path in $path_array
        if test -n "$path"  # Skip empty elements
            if not contains "$path" (string split ":" "$cleaned")
                if test -n "$cleaned"
                    set cleaned "$cleaned:$path"
                else
                    set cleaned "$path"
                end
            end
        end
    end

    set -gx $var_name "$cleaned"
end

# Deduplicate PATH-like variables
dedupe_path_var PATH

# Source the original activation script
source ".venv/bin/activate.fish"

# Note: Fish naturally propagates the exit code of the last command
