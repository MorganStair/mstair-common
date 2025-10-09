# File: python/plib_/xlogging/color_logger.py
"""
A logger that adds color and a prefix to messages.
"""

import re
from logging import CRITICAL, DEBUG, ERROR, INFO, WARNING
from typing import Any

from mstair.common.base import config as cfg
from mstair.common.xlogging.core_logger import CoreLogger
from mstair.common.xlogging.logger_constants import (
    RE_PATH_BACKSLASH,
)


color_logger = None
K_HMN = "Hmn"  # Fallback logger name used during script execution (e.g. cdk scripts)
K_HMN_CODE_ANALYZER = "HmnCodeAnalyzer"  # Fallback logger name used during code analysis
K_HMN_LAMBDA = "HmnLambda"  # Fallback logger name used during lambda execution


class ColorLogger(CoreLogger):
    def __init__(
        self,
        name: str | None = None,
        color: str = "magenta",
        prefix: str = "",
        suffix: str = "",
        caller_depth: int = 1,
    ):
        """
        A logger that adds color and a prefix to messages.

        :param name: The name of the logger.
        :param color: The color to use for messages.
        :param prefix: The prefix to add to messages.
        :param suffix: The suffix to add to messages.
        :param caller_depth: The depth from the caller to the ColorLogger methods.
        """
        super().__init__(name or self._get_fallback_logger_name())

        self.color = color
        """Color of the message part of the log output."""
        self.prefix = prefix
        """Prefix for the message part of the log output."""
        self.suffix: str = suffix
        """Suffix for the message part of the log output."""

        self.effective_stacklevel = caller_depth + 1
        """
        Stack level adjusted for ColorLogger wrapper method.

        - Problem:

        This creates the call chain:
        -> `caller`
        -> ColorLogger.`<level_method>()`
        -> CoreLogger.`log()`
        -> `_find_caller_frame()`

        - The +1 only accounts for the ColorLogger wrapper,
        - but CoreLogger.log() adds another +2 (via _INTERNAL_FRAME_OFFSET),
        - making the total offset caller_depth + 3,
        - which is likely too much.

        If this is accurate, then the effective_stacklevel should be `caller_depth + 2`, or ColorLogger should
        not add any offset and let CoreLogger handle it.
        """

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._custom_logger_log(DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._custom_logger_log(INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._custom_logger_log(WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._custom_logger_log(ERROR, msg, *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._custom_logger_log(CRITICAL, msg, *args, **kwargs)

    def _custom_logger_log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        formatted_msg = self.prefix + re.sub(RE_PATH_BACKSLASH, "/", msg) + self.suffix
        formatted_args = [
            re.sub(RE_PATH_BACKSLASH, "/", arg) if isinstance(arg, str) else arg for arg in args
        ]

        # Put self.color in the extra dict if it is already in the extra dict
        extra: dict[str, Any] = {"color": self.color, **kwargs.pop("extra", {})}

        # Put 'stacklevel' and 'extra' in the kwargs dict
        kwargs = {
            "stacklevel": self.effective_stacklevel,
            "extra": extra,
            **kwargs,
        }
        super().log(level, formatted_msg, *formatted_args, **kwargs)

    @staticmethod
    def _get_fallback_logger_name():
        if cfg.in_lambda() and not cfg.in_test_mode():
            return K_HMN_LAMBDA
        elif cfg.in_analysis_mode():
            return K_HMN_CODE_ANALYZER
        elif cfg.being_traced():
            return "HmnUnderTrace"
        else:
            return K_HMN


# End of file: src/mstair/common/xlogging/color_logger.py
