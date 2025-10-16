# File: python/plib_/xlogging/core_logger.py
"""
Structured logging with environment-driven configuration.

Example:
    >>> from mstair.common.xlogging import CoreLogger
    >>> logger = CoreLogger(__name__)
    >>> logger.info("Application started")
    >>>
    >>> with logger.prefix_with("[INIT]"):
    ...     logger.debug("Loading configuration")
    ...     logger.info("Configuration loaded")
    >>>
    >>> try:
    ...     risky_operation()
    ... except Exception:
    ...     logger.exception("Operation failed")

Features:
- Custom levels: TRACE, CONSTRUCT, SUPPRESS
- Stack-aware caller resolution
- Thread-safe prefix context manager
- Safe serialization of complex objects

Design:
- Only the root logger owns handlers/formatters; CoreLogger instances propagate.
- Log levels are controlled per-logger (via environment and LogLevelConfig).

Root Initialization Rationale:
- state is kept on the root logger attribute to avoid module-global leaks,
- only stderr is managed by this package,
- force reinit prunes only stderr handlers,
- default level fallback to WARNING ensures visibility when host apps leave root unset.

Future maintainers:
- Do not introduce a `_logging_initialized` flag or environment-sensitive modes.
- initialize_root() is the *only* supported entry point for root setup.
- Any testing or redirection framework should replace or wrap handlers
    externally, not by mutating this package
"""

from __future__ import annotations

import contextvars
import inspect
import logging
import os
import re
import sys
import traceback
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from types import FrameType, TracebackType
from typing import Any, ClassVar, TextIO

from mstair.common.base.types import PRIMITIVE_TYPES
from mstair.common.xdumps.xdumps_api import xdumps
from mstair.common.xlogging.logger_constants import TRACE
from mstair.common.xlogging.logger_util import LogLevelConfig

from ..base import config as cfg
from .frame_analyzer import StackFrameInfo
from .logger_constants import (
    CONSTRUCT,
    K_KLASS_NAME,
    initialize_logger_constants,
)
from .logger_formatter import CoreFormatter


__all__: list[str] = [
    "CoreLogger",
]

_LOG_FRAME_NOISE_METHODS: list[str] = [
    f"__{m}__" for m in ["get", "set", "delete", "enter", "exit", "call"]
]
_LOG_KWARGS_FORBIDDEN: set[str] = {"filename", "lineno", "msg", "args", "levelname", "levelno"}
_LOG_KWARGS_STANDARD: set[str] = {"exc_info", "stack_info", "stacklevel"}
_LOG_ROOT_ATTR_NAME = "_plib_corelogger_initialized"


_cached_caller_info: contextvars.ContextVar[StackFrameInfo | None] = contextvars.ContextVar(
    "cached_caller_info", default=None
)
_log_prefix: contextvars.ContextVar[str] = contextvars.ContextVar("log_prefix", default="")


class CoreLogger(logging.Logger):
    """
    Application logger that extends logging.Logger with:

    - Custom levels: TRACE, CONSTRUCT, SUPPRESS.
    - Accurate caller info using stack inspection.
    - Safe serialization of non-primitive args.
    - Structured methods (e.g. .construct()).
    - Prefix context manager for scoped message prefixes.
    - sys.excepthook support for uncaught exceptions.

    Handlers are not attached directly; all CoreLogger instances propagate
    to root logger, which holds a single stderr handler per initialize_root().
    """

    _INTERNAL_FRAME_OFFSET: ClassVar[int] = 2  # log() method + wrapper method (debug/info/etc)

    handlers: list[logging.Handler]

    def __init__(
        self,
        name: str,
        level: int | str | None = logging.NOTSET,
    ) -> None:
        """
        Initialize the CoreLogger with a name and log level.

        :param name: The name of the logger, typically the module or class name.
        :param level: The initial log level for the logger. Defaults to NOTSET.
        """
        initialize_logger_constants()

        levels: set[int | str] = {logging.NOTSET, "NOTSET", ""}
        level = level if level in levels or isinstance(level, int) else logging.NOTSET
        if level in levels:
            level = LogLevelConfig.get_instance().get_effective_level(name)
        super().__init__(name, level)

        root = logging.getLogger()
        root_level = root.getEffectiveLevel()
        if self.level < root_level:
            self.setLevel(root_level)

    def __repr__(self) -> str:
        level = self.getEffectiveLevel()
        level_name = logging.getLevelName(level)
        return "<{logger_class} '{name}' {level_name}={level}>".format(
            logger_class=self.__class__.__name__,
            name=self.name,
            level_name=level_name,
            level=level,
        )

    def rebind_stream(
        self,
        stream: TextIO | None = None,
    ) -> None:
        """
        Rebind this logger's StreamHandler to the given stream (default: current
        sys.stderr).

        This is intended only for controlled contexts (e.g., CLI rerouting), not
        for concurrent modification.

        - Closes and removes existing StreamHandlers.
        - Preserves level from the first removed StreamHandler (fallback:
          self.level).
        - Formatter preference:
            1) Keep existing CoreFormatter as-is.
            2) Replace stdlib Formatter or None with a new CoreFormatter.
            3) Never downgrade from CoreFormatter to stdlib Formatter.
        """
        preserved_formatter: logging.Formatter | None = None
        preserved_level: int | None = None

        retained_handlers: list[logging.Handler] = []
        for h in self.handlers:
            if isinstance(h, logging.StreamHandler):
                if preserved_formatter is None:
                    preserved_formatter = h.formatter
                    preserved_level = h.level
                with suppress(Exception):
                    h.close()
                continue
            retained_handlers.append(h)

        self.handlers = retained_handlers

        new_handler = logging.StreamHandler(stream or sys.stderr)
        new_handler.setFormatter(
            preserved_formatter
            if isinstance(preserved_formatter, CoreFormatter)
            else CoreFormatter()
        )
        new_handler.setLevel(preserved_level if preserved_level is not None else self.level)
        self.addHandler(new_handler)

    def log(self, level: int, *args: Any, **kwargs: Any) -> None:
        """
        Emit a log record with stack-aware context, preserving all handler/filter logic.

        Delegates to super().log() to ensure proper handler filtering, propagation,
        and level checking across the entire logging chain.
        """
        initialize_root()
        if cfg.in_analysis_mode():
            return
        if not self.isEnabledFor(level):
            return

        _validate_and_move_kwargs_to_extra(kwargs)
        _report_if_bad_stack_info(kwargs)
        _normalize_exc_info(kwargs)

        caller_requested_stacklevel: int = kwargs.pop("stacklevel", 1) + 1
        stacklevel: int = caller_requested_stacklevel + self._INTERNAL_FRAME_OFFSET
        found_frame_info: StackFrameInfo = _find_caller_frame(stacklevel)

        extra: dict[str, Any] = kwargs.setdefault("extra", {})
        if found_frame_info.f_locals_class_name:
            extra[K_KLASS_NAME] = found_frame_info.f_locals_class_name

        args = _normalize_unsupported_args(*args, **kwargs.get("extra", {}))

        # Apply prefix if set
        prefix = _log_prefix.get()
        msg: str
        if prefix and args:
            msg = args[0] if isinstance(args[0], str) else str(args[0])
            args = (f"{prefix}{msg}", *args[1:])
        elif prefix:
            msg = kwargs.get("msg", "")
            msg = msg if isinstance(msg, str) else str(msg)
            kwargs["msg"] = f"{prefix}{msg}"

        msg = args[0] if args else kwargs.get("msg", "")
        log_args: tuple[Any, ...] = args[1:] if len(args) > 1 else ()

        token: contextvars.Token[StackFrameInfo | None] = _cached_caller_info.set(found_frame_info)
        try:
            super().log(
                level,
                msg,
                *log_args,
                exc_info=kwargs.get("exc_info"),
                # stack_info can be bool or str (pre-formatted stack trace)
                # pyright doesn't know about the str overload in logging internals
                stack_info=kwargs.get("stack_info"),  # type: ignore
                stacklevel=1,
                extra=extra,
            )
        finally:
            _cached_caller_info.reset(token)

    def findCaller(
        self,
        stack_info: bool = False,
        stacklevel: int = 1,
    ) -> tuple[str, int, str, str | None]:
        """
        Override to use pre-computed frame info, avoiding duplicate stack
        walking.

        ``findCaller()`` uses a cached StackFrameInfo from the preceding log() call
        to avoid repeating expensive stack inspection. The cache is cleared
        immediately after use to prevent stale frame references and potential
        memory leaks. Future maintainers: do not retain cached_caller_info
        across log calls -- this could keep stack frames alive.

        Called by Logger._log() during the super().log() call to populate
        filename, lineno, and funcName in the LogRecord.

        :param stack_info: Whether to include stack trace information.
        :param stacklevel: Stack level offset (ignored when cached info exists).
        :return: Tuple of (filename, lineno, funcName, stack_info_string).
        """
        if (info := _cached_caller_info.get()) is not None:
            sinfo: str | None = None
            if stack_info:
                # Generate stack trace if requested
                sinfo = "".join(traceback.format_stack()[:-stacklevel])
            return (info.f_code_filename, info.frame.f_lineno, info.f_code_name, sinfo)

        # Fallback to parent implementation if no cached info
        return super().findCaller(stack_info=stack_info, stacklevel=stacklevel)
        # Control flow -> Logger._log() -> Handler.emit() -> CoreFormatter.format()

    def trace(self, *args: Any, **kwargs: Any) -> None:
        """Log a message at TRACE level (below DEBUG)."""
        level: int = kwargs.pop("level", TRACE)
        self.log(level, *args, **kwargs)

    def debug(self, *args: Any, **kwargs: Any) -> None:
        """Log a message at DEBUG level."""
        self.log(logging.DEBUG, *args, **kwargs)

    def construct(
        self,
        type_: type | str,
        id: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Log a structured construction event at CONSTRUCT level.

        Builds an indented string of the type and id, followed by serialized args. Does not treat first arg as
        format string.

        :param type_: Type or class of the constructed object (for label).
        :param id: Instance identifier.
        :param args: Optional metadata (e.g., dict).
        :param kwargs: Passed to log().
        """
        _type: str
        if isinstance(type_, str):
            _type = re.sub(r"^.*\.", "", type_)
        elif hasattr(type_, "__name__"):
            _type = type_.__name__
        else:
            _type = type(type_).__name__
        _type = _type.strip()

        _msg = f"\n  {_type}:\n    {id}"

        if args:
            extra: dict[str, Any] = kwargs.get("extra", {}).copy()
            for a in args:
                _msg += f", {xdumps(a, **extra)}".replace("\n", "\n    ")

        level: int = kwargs.pop("level", CONSTRUCT)
        self.log(level, _msg, **kwargs)

    def info(self, *args: Any, **kwargs: Any) -> None:
        """Log a message at INFO level."""
        self.log(logging.INFO, *args, **kwargs)

    def warning(self, *args: Any, **kwargs: Any) -> None:
        """Log a message at WARNING level."""
        self.log(logging.WARNING, *args, **kwargs)

    def error(self, *args: Any, **kwargs: Any) -> None:
        """Log a message at ERROR level."""
        self.log(logging.ERROR, *args, **kwargs)

    def critical(self, *args: Any, **kwargs: Any) -> None:
        """Log a message at CRITICAL level with a stack trace."""
        kwargs.setdefault(
            "stack_info", True
        )  # This is a useful deviation from standard Logger.critical()
        self.log(logging.CRITICAL, *args, **kwargs)

    def exception(self, *args: Any, **kwargs: Any) -> None:
        """Log a message at ERROR level with exception info and a stack trace.

        This method uses CoreLogger's custom log() method instead of bypassing it like super().exception().
        """
        kwargs.setdefault("exc_info", True)
        kwargs.setdefault("stack_info", True)
        self.log(logging.ERROR, *args, **kwargs)

    @contextmanager
    def prefix_with(self, prefix: str) -> Iterator[None]:
        """
        Context manager to prefix all log messages within the current context.

        Thread-safe and supports nesting. Uses contextvars to maintain
        per-context prefix state without modifying logger instances.

        :param prefix: The prefix string to prepend to all log messages.
        """
        formatted_prefix = (prefix + " > ") if not prefix.endswith("\n") else (prefix[:-1] + " >\n")

        # Stack prefixes for nested contexts
        current_prefix = _log_prefix.get()
        new_prefix = current_prefix + formatted_prefix if current_prefix else formatted_prefix

        token = _log_prefix.set(new_prefix)
        try:
            yield
        finally:
            _log_prefix.reset(token)

    @property
    def sys_excepthook(
        self,
    ) -> Callable[[type[BaseException], BaseException, TracebackType | None], None]:
        """Returns a sys_excepthook that uses this logger."""

        def sys_excepthook(
            exc_type: type[BaseException],
            exc_value: BaseException,
            exc_traceback: TracebackType | None,
        ) -> None:
            """An alternative to the default sys.excepthook that logs uncaught exceptions via logger.critical()."""
            tb = traceback.extract_tb(exc_traceback)
            msg = xdumps(exc_value, rshift=4)
            if tb:
                frame = tb[-1]
                log_record = sys_excepthook_logger.makeRecord(
                    name=sys_excepthook_logger.name,
                    level=logging.CRITICAL,
                    fn=frame.filename if frame.filename else "<unknown file>",
                    lno=frame.lineno or 1,
                    msg=msg,
                    args=(),
                    exc_info=(exc_type, exc_value, exc_traceback),
                    func=frame.name if frame.name else "<unknown function>",
                )
                sys_excepthook_logger.handle(log_record)
            else:
                sys_excepthook_logger.critical(
                    f"\nUncaught exception:\n    {msg}",
                    exc_info=(exc_type, exc_value, exc_traceback),
                    stack_info=True,
                )

        sys_excepthook_logger: logging.Logger | CoreLogger = self
        return sys_excepthook


def initialize_root(
    fmt: str | None = None,
    datefmt: str | None = None,
    level: int | str | None = None,
    force: bool = False,
) -> None:
    """
    Idempotently configure the root logger for CoreLogger.

    Public entry point for root setup. Tracks state on the root logger
    (attribute: _plib_corelogger_initialized), never in a module-global.

    Behavior:
    - Ensures exactly one stderr StreamHandler with CoreFormatter exists.
    - If `force=True`, removes and recreates the stderr handler.
    - If `force=False` and already initialized, returns immediately (idempotent).
    - Sets root level to `level` if provided, otherwise uses WARNING if NOTSET.
    - Does not modify non-stderr handlers owned by the host application.

    This design keeps responsibilities clear:
    - Initialization policy (idempotence, pruning, level) lives here.
    - Handler/formatter mechanics are delegated to a private helper.

    :param fmt: Format string. Defaults to LOG_FORMAT or package default.
    :param datefmt: Date format. Defaults to LOG_DATEFMT or package default. If it contains
        no percent directives, timestamps are removed from the format.
    :param level: Root logger level (int or name). If None and root is NOTSET, WARNING is used.
    :param force: Reinitialize even if already initialized (prunes existing stderr handlers).
    """
    root: logging.Logger = logging.getLogger()
    if getattr(root, _LOG_ROOT_ATTR_NAME, False) and not force:
        return
    setattr(root, _LOG_ROOT_ATTR_NAME, True)

    initialize_logger_constants()

    # Prune stderr handlers on force to avoid duplicates
    if force:
        root.handlers = [
            h
            for h in root.handlers
            if not (isinstance(h, logging.StreamHandler) and h.stream is sys.stderr)
        ]

    _ensure_stderr_coreformatter(fmt=fmt, datefmt=datefmt)

    # Apply level policy
    if level is not None:
        if isinstance(level, str):
            level = logging.getLevelNamesMapping().get(level.upper(), logging.WARNING)
        root.setLevel(level)
    elif root.getEffectiveLevel() == logging.NOTSET:
        root.setLevel(logging.WARNING)


def _ensure_stderr_coreformatter(*, fmt: str | None = None, datefmt: str | None = None) -> None:
    """
    Ensure the root logger has one stderr handler using CoreFormatter.

    - If no stderr StreamHandler exists, create one with CoreFormatter.
    - If one exists without CoreFormatter, upgrade its formatter in place.
    - Never touches non-stderr handlers.

    Env overrides:
    - LOG_FORMAT supplies the format string fallback.
    - LOG_DATEFMT supplies the date format fallback; if it has no '%' tokens,
        timestamp is stripped from the final format.

    Rationale:
        This helper only manages the stderr StreamHandler used by CoreLogger.
        Other handlers (e.g., file, syslog, structured JSON) belong to the host
        application and must not be altered automatically.
    """
    fmt = fmt or os.environ.get(
        "LOG_FORMAT",
        r"%(levelName)s %(asctime)s %(fileAndLine)s %(klassAndMethod)s %(message)s",
    )
    env_datefmt: str = os.environ.get("LOG_DATEFMT", "%-I:%M%p")
    datefmt = env_datefmt if datefmt is None else datefmt
    if "%" not in datefmt:
        fmt = re.sub(r"\s*%\(asctime\)s\s*", " ", fmt)
        datefmt = None

    root: logging.Logger = logging.getLogger()
    stderr_handlers: list[logging.StreamHandler[TextIO]] = [
        h for h in root.handlers if isinstance(h, logging.StreamHandler) and h.stream is sys.stderr
    ]
    if not stderr_handlers:
        h: logging.StreamHandler[TextIO] = logging.StreamHandler(sys.stderr)
        h.setFormatter(CoreFormatter(fmt, datefmt))
        root.addHandler(h)
        return

    if not any(isinstance(h.formatter, CoreFormatter) for h in stderr_handlers):
        stderr_handlers[0].setFormatter(CoreFormatter(fmt, datefmt))


def _find_caller_frame(stacklevel: int) -> StackFrameInfo:
    """
    Find the appropriate caller frame, skipping logging noise frames.

    The walk continues until the number of non-noise frames reaches the
    requested stacklevel - 1. This compensates for CoreLogger's internal call
    depth.
    """
    current_frame: FrameType | None = inspect.currentframe()
    if current_frame is None:
        raise RuntimeError("Cannot retrieve current stack frame for caller resolution")

    found_frame_info: StackFrameInfo | None = None
    target_frame_depth: int = stacklevel
    frames_walked: int = 0
    noise_frames_seen: int = 0

    while current_frame is not None:
        found_frame_info = StackFrameInfo.from_raw_frame(
            raw_frame=current_frame,
            stack_position=frames_walked,
        )

        if _is_noise_frame(
            f_code_filename=found_frame_info.f_code_filename,
            f_code_filename_relative=found_frame_info.code_filename_relative,
            f_code_name=found_frame_info.f_code_name,
            f_locals_self=found_frame_info.f_locals_self,
        ):
            noise_frames_seen += 1
        elif (frames_walked - noise_frames_seen) >= target_frame_depth - 1:
            break

        current_frame = current_frame.f_back
        frames_walked += 1
    if found_frame_info is None:
        raise RuntimeError(
            f"Stack walk completed without finding valid caller frame (walked {frames_walked} frames)"
        )
    return found_frame_info


def _is_noise_frame(
    *,
    f_code_filename: str,
    f_code_filename_relative: str,
    f_code_name: str,
    f_locals_self: object | None,
) -> bool:
    """Determine if the frame is a noise frame, i.e., not relevant for logging."""

    _skip_filename_patterns: list[str] = [
        r"<string>",
        *_LOG_FRAME_NOISE_METHODS,
    ]
    if any(re.search(p, f_code_filename_relative, re.IGNORECASE) for p in _skip_filename_patterns):
        return True
    if any(re.search(p, f_code_filename, re.IGNORECASE) for p in _skip_filename_patterns):
        return True
    if not f_locals_self and f_code_name == "__init__":
        return True

    return bool(
        "/lib/concur" in f_code_filename_relative.lower() or "/lib/concur" in f_code_filename.lower()
    )


def _validate_and_move_kwargs_to_extra(kwargs: dict[str, Any]) -> None:
    """
    Validates and mutates kwargs by moving non-standard keys into extra dict.

    :param kwargs: The keyword arguments passed to the log() method.
    :raises ValueError: If any forbidden keys are found in kwargs.
    """
    for _key, _value in list(kwargs.items()):
        if _key in _LOG_KWARGS_FORBIDDEN:
            raise ValueError(
                f"Invalid keyword argument '{_key}={xdumps(_value, **kwargs.get('extra', {}))}'"
            )
        if _key not in _LOG_KWARGS_STANDARD:
            kwargs.pop(_key)
            kwargs.setdefault("extra", {})[_key] = _value


def _normalize_unsupported_args(*args: Any, **kwargs: Any) -> tuple[Any, ...]:
    """
    Convert non-primitive arg types to JSON strings using xdumps.

    :param Any *args: The log() arguments, which may contain non-primitive types.
    :param Any **kwargs: Additional keyword arguments, which may include logging extras.
    :return tuple[Any, ...]: The normalized arguments, with non-primitive types converted to strings.
    """
    num_fmt_params = len(args) - 1
    if num_fmt_params > 0:
        if not isinstance(args[0], str):
            logging.getLogger(__name__).warning(
                "First log() argument must be a format string if args are provided: %r", args[0]
            )
        else:
            try:
                _ = args[0] % tuple(args[1:])
            except (TypeError, ValueError) as e:
                logging.getLogger(__name__).warning(
                    "Bad log format string or args: %r %% %r failed (%s: %s)",
                    args[0],
                    args[1:],
                    type(e).__name__,
                    e,
                )

    arg_list: list[Any] = []
    for arg in args:
        if isinstance(arg, PRIMITIVE_TYPES):
            arg_list.append(arg)
        else:
            try:
                arg_string = xdumps(arg, **kwargs)
                arg_list.append(arg_string)
            except Exception as e:
                arg_list.append(f"<unserializable: {type(arg).__name__}: {e}>")
    _args = tuple(arg_list)
    return _args


def _normalize_exc_info(kwargs: dict[str, Any]) -> None:
    """Normalize exc_info to valid value, logging issues."""
    exc_info = kwargs.get("exc_info")

    if exc_info is None or isinstance(exc_info, bool):
        return

    if not isinstance(exc_info, tuple) or len(exc_info) != 3:
        logging.getLogger(__name__).warning(
            f"Invalid exc_info (not 3-tuple): {type(exc_info).__name__}, disabling"
        )
        kwargs["exc_info"] = False
        return

    _type, _value, _tb = exc_info
    if not (isinstance(_type, type) and issubclass(_type, BaseException)):
        logging.getLogger(__name__).warning(
            f"Invalid exc_info[0]: expected exception type, got {type(_type).__name__}"
        )
        kwargs["exc_info"] = False
        return
    if not isinstance(_value, BaseException):
        logging.getLogger(__name__).warning(
            f"Invalid exc_info[1]: expected exception instance, got {type(_value).__name__}"
        )
        kwargs["exc_info"] = False
        return
    if not isinstance(_tb, (TracebackType, type(None))):
        logging.getLogger(__name__).warning(
            f"Invalid exc_info[2]: expected traceback, got {type(_tb).__name__}"
        )
        kwargs["exc_info"] = False
        return


def _report_if_bad_stack_info(kwargs: dict[str, Any]) -> None:
    """
    Report invalid stack_info values via debug log if the stack_info is bad.

    - None or bool is acceptable (no stack or capture current).
    - str must be a full stack trace (40 chars with "File" or "Traceback").

    Never raises or mutates. Reports to the module debug logger for visibility.
    """
    val = kwargs.get("stack_info")
    if val is None or isinstance(val, bool):
        return
    if isinstance(val, str):
        text = val.strip()
        if len(text) >= 40 and ("File " in text or "Traceback" in text):
            return
        # Report via this module's debug logger to avoid recursive emission.
        logging.getLogger(__name__).warning(
            f"Invalid stack_info string (too short or malformed): {text!r}"
        )
    else:
        # Report via this module's debug logger to avoid recursive emission.
        logging.getLogger(__name__).warning(f"Invalid stack_info type: {type(val).__name__}")


# End of file: src/mstair/common/xlogging/core_logger.py
