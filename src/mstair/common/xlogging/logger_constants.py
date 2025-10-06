# File: python/plib_/xlogging/logger_constants.py

import logging


K_KLASS_NAME = "klass_name"
RE_PATH_BACKSLASH = r"\\(?=\w{2,})"

CONSTRUCT = logging.INFO - 1  # (19) LOG.construct() will not output at INFO level
TRACE = logging.DEBUG - 1  # (9) LOG.trace() will not output at DEBUG level
SUPPRESS = -1  # Custom level for logs that will never be shown e.g., for internal use only


_logging_constants_initialized = False


def initialize_logger_constants():
    """Initialize custom logging levels if not already initialized."""
    global _logging_constants_initialized
    if _logging_constants_initialized:
        return
    _logging_constants_initialized = True
    for key, value in {
        "TRACE": TRACE,
        "SUPPRESS": SUPPRESS,
        "CONSTRUCT": CONSTRUCT,
    }.items():
        if key not in logging.getLevelNamesMapping():
            logging.addLevelName(value, key)


# End of file: python/plib_/xlogging/logger_constants.py
