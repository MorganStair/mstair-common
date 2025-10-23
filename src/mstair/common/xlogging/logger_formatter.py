import ctypes
import logging
import os
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any, Literal

import pytz
from colorama import Fore

import mstair.common.base.config as cfg
from mstair.common.base.fs_helpers import fs_find_pyproject_toml
from mstair.common.xdumps.xdumps_api import xdumps
from mstair.common.xlogging.logger_constants import (
    RE_PATH_BACKSLASH,
)

from .logger_constants import CONSTRUCT, K_KLASS_NAME, TRACE


__all__ = ["CoreFormatter", "get_color_code", "rgb_code"]


FormatStyle = Literal["%", "{", "$"]
"""
Format string style accepted by `CoreFormatter` (and `logging.Formatter`):

- `"%"` for percent-format (`%`)
- `"{"` for `str.format()` (`{}`)
- `"$"` for `string.Template` (`$`)

For more information, see the [Python logging Formatter documentation](https://docs.python.org/3/library/logging.html#formatter-objects).
"""


def rgb_code(r: int, g: int, b: int) -> str:
    """
    Convert RGB values to ANSI escape code for terminal color output.

    :param r: Red component (0-255)
    :param g: Green component (0-255)
    :param b: Blue component (0-255)
    :return str: ANSI escape code for the specified RGB color.
    """
    return f"\033[38;2;{max(0, min(255, r))};{max(0, min(255, g))};{max(0, min(255, b))}m"


RGB_CALLER_0 = rgb_code(3 << 4, 12 << 4, 10 << 4)
RGB_CALLER_1 = rgb_code(4 << 4, 8 << 4, 10 << 4)
COLOR_MAP = {
    # Code location colors
    "file": RGB_CALLER_1,
    "fileAndLine": RGB_CALLER_1,
    "line": RGB_CALLER_1,
    # Python related colors
    "klass": RGB_CALLER_0,
    "klassAndMethod": RGB_CALLER_0,
    "method": RGB_CALLER_0,
    "module": RGB_CALLER_0,
    "moduleAndMethod": RGB_CALLER_0,
    # "name": RGB_CALLER_0,
    # Colors related for log levels
    "TRACE": rgb_code(96, 0, 64),  # Mauve for trace logs
    "DEBUG": rgb_code(0, 0, 0),  # Dark gray for debug logs
    "INFO": rgb_code(184, 184, 216),  # Light gray for info logs
    "WARNING": rgb_code(192, 176, 0),  # Yellow for warnings
    "ERROR": rgb_code(224, 128, 0),  # Orange for errors
    "CRITICAL": rgb_code(255, 64, 64),  # Red for critical errors
    "CONSTRUCT": rgb_code(176, 176, 224),
    "SUPPRESS": rgb_code(0, 0, 128),  # Dark blue for suppressed logs
    None: Fore.RESET,
}


def get_color_code(key: Any = None) -> str | Any:
    # Disable color codes in code analyzer and lambda functions
    if not cfg.in_desktop_mode():
        return ""

    # Any key that is effectively False or RESET will return the reset color code
    if key in {"", "RESET"} or key is None:
        return Fore.RESET

    # Check if the key is in the COLOR_MAP
    if key in COLOR_MAP:
        return COLOR_MAP[key]

    # Check if the key is a hex color code
    if isinstance(key, str) and key.startswith("#"):
        return rgb_code(*[int(key[i : i + 2], 16) for i in (1, 3, 5)])

    # Clean up the key then check if it is a valid color from the Fore module
    _clean_key = key.upper()
    if "BRIGHT" in _clean_key:
        _clean_key = _clean_key.replace("BRIGHT", "LIGHT")
    if "LIGHT" in _clean_key and not _clean_key.endswith("_EX"):
        _clean_key += "_EX"
    if _clean_key in dir(Fore):
        return getattr(Fore, _clean_key)

    # Fall back to the reset color code
    return Fore.RESET


K_LOG_REPLACE_BACKSLASHES = "log_raw_msg"
K_COLOR = "color"
WITH_STREAM_HANDLER_HACK = False
WITH_REPLACE_BACKSLASHES = False


class CoreFormatter(logging.Formatter):
    """
    Custom formatter for CoreLogger that adds file and line information,
    class and method names, and color-coded log levels.
    """

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: FormatStyle = "%",
        validate: bool = True,
        *,
        defaults: dict[str, Any] | None = None,
        _debug: Any = None,
    ) -> None:
        """
        Initialize the CoreFormatter with a format string, date format, and style.

        :param fmt: The format string for log messages.
        :param datefmt: The date format string for log timestamps.
        :param style: The style for the format string (default is "%").
        :param validate: Whether to validate the format strings (default is True).
        :param defaults: Default values for format fields (used only if style="{" or "$").
        """
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate, defaults=defaults)
        self.est_tz = pytz.timezone("US/Eastern")
        self._debug = _debug

    def format(self, record: logging.LogRecord) -> str:
        # SRD: Main entry point for log record formatting
        # Called from: StreamHandler.emit()
        # Calls: super().format() -> apply_message_colors() -> message_filter()

        record.fileAndLine = self.format_fileAndLine(record.pathname, record.lineno)
        record.klassAndMethod = self.format_klassAndMethod(record)
        record.moduleAndMethod = self.format_moduleAndMethod(record.module, record.funcName)
        record.method = self.format_method(record.funcName)
        record.levelName = self.format_levelName(record.levelname)
        record.name = self.format_name(record)

        if WITH_STREAM_HANDLER_HACK:
            if record.levelno == CONSTRUCT:
                record.levelno = logging.INFO
            elif record.levelno == TRACE:
                record.levelno = logging.DEBUG

        try:
            message_str = super().format(record)
            message_str = self.apply_message_colors(record, message_str)
        except Exception as exc:
            message_str = format_logging_error(record, exc, self._debug)

        try:
            message_str = self.message_filter(message_str)
        except Exception as exc:
            message_str += f"\n(LOGGING FILTER ERROR: {exc!r})\n"
        return message_str

    @staticmethod
    def format_file(file: str) -> str:
        """
        Formats the file path relative to the project root if possible,
        otherwise falls back to the original scriptdir-relative logic.
        """
        if not file:
            return "<unknown file>"

        try:
            project_root = fs_find_pyproject_toml(start_dir=Path(file).parent)
            if project_root is None:
                file = Path(file).absolute().as_posix()
            else:
                file = Path(file).relative_to(project_root).as_posix()
        except Exception:
            # Fall back to scriptdir-relative logic
            if not sys.path or not sys.path[0]:
                return Path(file).as_posix()
            if " " in file and os.name == "nt":
                abspath = os.path.abspath(file)
                buffer = ctypes.create_unicode_buffer(260)
                result = ctypes.windll.kernel32.GetShortPathNameW(abspath, buffer, len(buffer))
                if result != 0:
                    file = buffer.value
            scriptdir = sys.path[0]
            try:
                file = Path(file).relative_to(scriptdir).as_posix()
            except ValueError:
                file = Path(file).absolute().as_posix()
            file = Path(file).as_posix()

        if cfg.in_lambda() and not cfg.in_test_mode():
            file = re.sub(r"^.*packages/hmn_", "hmn_", file)
        return file

    def format_fileAndLine(self, file: str, lineno: int) -> str:
        # SRD: Format file path and line number with colors
        # Called from: format()
        # Calls: format_file() -> get_color_code()
        file = self.format_file(file)
        fileAndLine = file + ":" + str(lineno)
        if not fileAndLine.startswith("."):
            fileAndLine = get_color_code("fileAndLine") + fileAndLine + get_color_code()
        return fileAndLine

    @staticmethod
    def format_klassAndMethod(record: logging.LogRecord) -> str:
        # SRD: Format class and method names with colors
        # Called from: format()
        # Calls: get_color_code()
        klass_name = getattr(record, K_KLASS_NAME, record.module)

        if not any(char.isupper() for char in klass_name):
            klassAndMethod = (
                record.funcName if record.funcName == "<module>" else f"{record.funcName}()"
            )  # klassAndMethod = "function()"
        elif record.funcName == "__init__":
            klassAndMethod = f"{klass_name}()"  # klassAndMethod = "Klass()"
        else:
            klassAndMethod = f"{klass_name}.{record.funcName}()"  # klassAndMethod = "Klass.method()"

        result: str = get_color_code("klassAndMethod") + klassAndMethod + get_color_code()
        return result

    @staticmethod
    def format_levelName(levelname: str) -> str:
        # SRD: Format log level name with colors
        # Called from: format()
        # Calls: get_color_code()
        levelName = get_color_code(levelname) + levelname + get_color_code()
        return levelName

    @staticmethod
    def format_method(funcName: str) -> str:
        # SRD: Format method name with colors
        # Called from: format()
        # Calls: get_color_code()
        method: str = get_color_code("method") + funcName + "()" + get_color_code()
        return method

    @staticmethod
    def format_moduleAndMethod(module: str, funcName: str) -> str:
        # SRD: Format module and method name with colors
        # Called from: format()
        # Calls: get_color_code()
        moduleAndMethod = (
            get_color_code("moduleAndMethod") + module + "." + funcName + "()" + get_color_code()
        )
        return moduleAndMethod

    @staticmethod
    def apply_message_colors(record: logging.LogRecord, formatted_message: str) -> str:
        # SRD: Apply colors and processing to an already-formatted message
        # Called from: format() after super().format()
        # Calls: get_color_code()
        color_key = getattr(record, K_COLOR, record.levelname)

        _replace_backslashes = getattr(record, K_LOG_REPLACE_BACKSLASHES, WITH_REPLACE_BACKSLASHES)
        if _replace_backslashes:
            formatted_message = re.sub(RE_PATH_BACKSLASH, "/", formatted_message)

        color_code = get_color_code(color_key)
        reset_code = get_color_code()
        return color_code + formatted_message + reset_code

    @staticmethod
    def format_name(record: logging.LogRecord) -> str:
        # SRD: Format logger name with colors
        # Called from: format()
        # Calls: get_color_code()
        _color_key = getattr(record, K_COLOR, record.levelname)
        _name = get_color_code(_color_key) + "[" + record.name + "]" + get_color_code()
        return _name

    def formatException(
        self,
        ei: (
            tuple[type[BaseException], BaseException, TracebackType | None]
            | tuple[None, None, None]
            | BaseException
            | bool
            | None
        ),
    ) -> str:
        """
        Normalize `ei` to a stdlib-compatible 3-tuple, then format and filter.

        :param ei: Exception info in flexible forms (tuple/exception/bool/None).
        :return: Filtered string produced by the parent formatter.
        """
        # Normalize irregular inputs to a tuple as logging expects.
        if ei is True:
            cur = sys.exc_info()
            ei = (cur[0], cur[1], cur[2]) if cur[0] is not None else (None, None, None)
        elif ei in {False, None}:
            ei = (None, None, None)
        elif isinstance(ei, BaseException):
            ei = (type(ei), ei, ei.__traceback__)

        message = super().formatException(ei)  # type: ignore[arg-type]
        return self.message_filter(message)

    def formatTime(self, record: Any, datefmt: str | None = None) -> str:
        # SRD: Format timestamp with timezone and colors
        # Called from: logging.Formatter.format()
        # Calls: get_color_code()
        _datetime = datetime.fromtimestamp(record.created, self.est_tz)
        _result: str = ""
        if datefmt:
            try:
                datefmt = datefmt.replace(r"%-", "%")
                _result = _datetime.strftime(datefmt)
                _result = _result.replace("AM", "am").replace("PM", "pm").lstrip("0")
            except ValueError as e:
                _stack_trace = (
                    "".join(traceback.format_exception(type(e), e, e.__traceback__))
                    .rstrip()
                    .replace("\n", "\n  ")
                )
                print(f"{_stack_trace}: '{datefmt}'", file=sys.stderr)

        _result = _result or _datetime.isoformat()
        _result = get_color_code(record.levelname) + _result + get_color_code()
        return _result

    def message_filter(self, message: str, excludes: Any = None) -> str:
        # SRD: Filter and format traceback messages, removing noise paths
        # Called from: format() and formatException()
        # Calls: format_fileAndLine() -> get_color_code()
        """
        Filters and formats error messages by removing specified paths and formatting file locations.

        :message (str): The error message to filter.
        :excludes (list, optional): List of regex patterns for paths to exclude.
                Defaults to [r'[/\\].venv', r'[/\\]Program Files', '<frozen'].
        :returns (str): Filtered and reformatted message with excluded paths removed.
        """

        excludes = excludes or ["[/\\\\].venv", "[/\\\\]Program Files", "<frozen"]
        lines = message.splitlines()
        filtered_lines: list[str] = []
        skip_indent_lines = False

        for line in lines:
            if skip_indent_lines and line.startswith("    "):
                continue
            skip_indent_lines = False

            match = re.search(r'^  File "([^"]+)", line (\d+), in (.*?)$', line)
            if match and any(re.search(ex, match.group(1)) for ex in excludes):
                skip_indent_lines = True
                continue

            if match:
                fileAndLine = self.format_fileAndLine(match.group(1), int(match.group(2)))
                klassAndMethod = (
                    get_color_code("klassAndMethod") + match.group(3) + "()" + get_color_code()
                )
                filtered_lines.append(f"  {fileAndLine} {klassAndMethod}")
            else:
                filtered_lines.append(line)

        return "\n".join(filtered_lines)


def format_logging_error(record: logging.LogRecord, exc: Exception, debug_config: Any = None) -> str:
    """
    Generate a formatted error message when log record formatting fails.

    :param record: The LogRecord that failed to format
    :param exc: The exception that occurred during formatting
    :param debug_config: Debug configuration object (checks for 'verbose' attribute)
    :return: Formatted error message string
    """
    posix_path = Path(getattr(record, "pathname", "<unknown>")).as_posix()
    line = getattr(record, "lineno", "?")
    full_traceback = traceback.format_exc()

    message_lines = [
        "Internal error: Failed to format log record",
        f"{posix_path}:{line}",
        f"{type(exc).__name__}: {exc}",
    ]

    if getattr(debug_config, "verbose", False):
        message_lines.extend(
            [
                "",
                "xdumps(record):",
                f"  {xdumps(vars(record), **getattr(record, 'extra', {}))}",
            ],
        )
    else:
        message_lines.extend(
            [
                f"record.msg: {getattr(record, 'msg', None)!r}",
                f"record.args: {getattr(record, 'args', None)!r}",
                "",
            ],
        )

    message_lines.extend(full_traceback.splitlines())
    message_lines.extend(["."])

    return "\n>> " + "\n>> ".join(message_lines) + "\n\n"
