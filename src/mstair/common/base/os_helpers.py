# File: python/plib_/base/os_helpers.py

from __future__ import annotations

import os


os_helpers = None


def os_environ_truthy(var_name: str, default: bool = False) -> bool:
    """Check if an environment variable is set to a truthy value.

    Truthy values are: "1", "true", "yes", "on" (case-insensitive).
    Falsy values are: "0", "false", "no", "off" (case-insensitive).
    If the variable is not set, returns the specified default value.

    Args:
        var_name (str): The name of the environment variable to check.
        default (bool): The default value to return if the variable is not set.

    Returns:
        bool: True if the variable is set to a truthy value, False if set to a falsy value,
              or the default value if not set.
    """
    truthy_values = {"1", "true", "yes", "on"}
    falsy_values = {"0", "false", "no", "off"}

    value = os.getenv(var_name)
    if value is None:
        return default

    value_lower = value.strip().lower()
    if value_lower in truthy_values:
        return True
    elif value_lower in falsy_values:
        return False
    else:
        return default  # Return default for unrecognized values


# End of file: python/plib_/base/os_helpers.py
