# File: src/mstair/common/xlogging/logger_util.py
"""
Environment variable-driven log level configuration.

Two sources are supported:
- Pattern-based DSL strings in LOG_LEVEL / LOG_LEVELS
- Per-logger overrides in variables like LOG_LEVEL_<NAME>

See LogLevelConfig for resolution rules.
"""

from __future__ import annotations

import fnmatch
import logging
import os
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import ClassVar, Final, NamedTuple

from mstair.common.base.fs_helpers import fs_load_dotenv
from mstair.common.xlogging.logger_constants import initialize_logger_constants


__all__ = ["LogLevelConfig"]

_LOG_VAR_FRAGMENT_SEPARATOR_RX: Final[re.Pattern[str]] = re.compile(r"[;, ]+")
_LOG_VAR_ASSIGNMENT_OPERATOR_RX: Final[re.Pattern[str]] = re.compile(r"[:=]+")

_log_level_config_instance: LogLevelConfig | None = None


@dataclass(slots=True)
class LogEnvVar:
    """
    Parsed representation of a log-level environment variable.

    Recognizes names starting with LOG_LEVEL or LOG_LEVELS.
    Encodes the base name, target module (with "__" -> "_" and "_" -> "."),
    and the raw value.
    """

    NAME_RX: ClassVar[re.Pattern[str]] = re.compile(
        r"""
        ^(?P<BASENAME>LOG_LEVELS?)          # LOG_LEVEL or LOG_LEVELS
        (?P<SUFFIX>(?:_[A-Z][A-Z0-9_]*)*)$  # optional suffix
        """,
        re.VERBOSE,
    )

    name: str = field(default="", init=True, repr=False)  # Useful for debugging
    basename: str = field(default="", init=True, repr=False)  # Useful for debugging
    module: str = field(default="", init=True, repr=True)
    value: str = field(default="", init=True, repr=False)

    @classmethod
    def from_env_var(cls, name: str, value: str) -> LogEnvVar | None:
        """Return a LogEnvVar if the given (name, value) is valid, else None."""
        re_match: re.Match[str] | None = LogEnvVar.NAME_RX.match(name)
        if re_match is not None:
            match: dict[str, str] = re_match.groupdict()
            basename: str = match["BASENAME"]
            suffix: str = match["SUFFIX"].lstrip("_")
            if not suffix or suffix.upper() == "ROOT":
                module = ""  # default/root
            else:
                module = suffix.replace("__", "\0").replace("_", ".").replace("\0", "_").lower()

            instance = cls(name=name, value=value, basename=basename, module=module)
            return instance
        return None

    @classmethod
    def from_environ(cls) -> Iterator[LogEnvVar]:
        """Yield LogEnvVar instances for all matching environment variables."""
        fs_load_dotenv()
        for name, value in sorted(os.environ.items(), reverse=True):
            env_var = cls.from_env_var(name, value)
            if env_var:
                yield env_var


class LogEnvPatternLevel(NamedTuple):
    """Mapping from a pattern string to an integer log level."""

    pattern: str
    level: int


@dataclass(slots=True)
class LogLevelConfig:
    """
    Resolve log levels using environment variables.

    Supports:
    - DSL patterns in LOG_LEVEL / LOG_LEVELS
    - Explicit per-logger overrides in LOG_LEVEL_<NAME>

    Precedence: exact > ancestor > glob > default > fallback.
    """

    pattern_to_level: dict[str, int] = field(default_factory=dict, init=True, repr=True)
    _level_names_mapping: dict[str, int] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.pattern_to_level:
            self.update_from_environment()

    def update_from_environment(self) -> None:
        """Rebuild pattern->level mappings from current environment."""
        self.level_names_mapping.clear()  # invalidate cache
        self.pattern_to_level.clear()  # reset the mapping we are building
        for var in LogEnvVar.from_environ():
            for dsl in self.parse_log_var(var):
                self.pattern_to_level[dsl.pattern] = dsl.level

    def get_effective_level(self, logger_name: str, *, default: int = logging.WARNING) -> int:
        """Return the effective log level for a logger name."""
        name_lc = logger_name.lower()

        # Exclude the default entry from structural matching.
        lc_map: dict[str, int] = {k.lower(): v for k, v in self.pattern_to_level.items() if k != ""}

        # 1) Exact
        effective_level: int | None = lc_map.get(name_lc)
        if effective_level is not None:
            return effective_level

        # 2) Ancestor
        for anc in LogLevelConfig._ancestors(name_lc):
            if anc in lc_map:
                return lc_map[anc]

        # 3) Best glob (exclude default)
        best_level: int | None = None
        best_score: int = -1
        for pat, level in self.pattern_to_level.items():
            if pat == "" or not LogLevelConfig._is_glob_pattern(pat):
                continue
            pat_lc = pat.lower()
            if fnmatch.fnmatch(name_lc, pat_lc):
                score = LogLevelConfig._glob_specificity(pat_lc)
                if score > best_score:
                    best_score = score
                    best_level = level
        if best_level is not None:
            return best_level

        # 4) Global/default
        default_level = self.pattern_to_level.get("")
        if default_level is not None:
            return default_level

        # 5) Fallback
        return default

    @classmethod
    def get_instance(cls) -> LogLevelConfig:
        """Return the singleton LogLevelConfig instance, creating it if needed."""
        global _log_level_config_instance
        if not _log_level_config_instance:
            initialize_logger_constants()
            _log_level_config_instance = LogLevelConfig()
        return _log_level_config_instance

    @property
    def level_names_mapping(self) -> dict[str, int]:
        """Cached uppercase level-name mapping from logging (call clear() to invalidate)."""
        if not self._level_names_mapping:
            self._level_names_mapping = {
                k.upper(): v
                for k, v in logging.getLevelNamesMapping().items()
                if isinstance(k, str) and k.isupper() and isinstance(v, int)
            }
        return self._level_names_mapping

    def parse_log_var(self, var: LogEnvVar) -> Iterator[LogEnvPatternLevel]:
        """Parse one LogEnvVar into pattern->level mappings."""
        for fragment in _LOG_VAR_FRAGMENT_SEPARATOR_RX.split(var.value):
            pattern_level = fragment.strip()
            if not pattern_level:
                continue

            parts = _LOG_VAR_ASSIGNMENT_OPERATOR_RX.split(pattern_level, maxsplit=1)
            if len(parts) == 2:
                pattern = parts[0].strip().strip("'\"")
                level_name = parts[1].strip().strip("'\"").upper()
            else:
                pattern = ""  # bare level -> default/root
                level_name = parts[0].strip().strip("'\"").upper()

            if var.module:
                if pattern not in ("", "root"):
                    pattern = f"{var.module}.{pattern}"
                else:
                    pattern = var.module
            if pattern.lower() == "root":
                pattern = ""

            level_num: int = self.level_names_mapping.get(level_name, logging.NOTSET)
            if level_num == logging.NOTSET:
                continue

            yield LogEnvPatternLevel(pattern, level_num)

    @staticmethod
    def _is_glob_pattern(pattern: str) -> bool:
        """Return True if the pattern contains glob wildcards."""
        return any(ch in pattern for ch in ("*", "?", "["))

    @staticmethod
    def _ancestors(logger_name: str) -> list[str]:
        """Return ancestor names of a dotted logger path, most specific first."""
        parts = logger_name.split(".")
        result: list[str] = []
        while len(parts) > 1:
            parts = parts[:-1]
            result.append(".".join(parts))
        return result

    @staticmethod
    def _glob_specificity(pattern: str) -> int:
        """Return specificity score: length of fixed prefix before any wildcard."""
        first = min((i for i, ch in enumerate(pattern) if ch in "*?["), default=len(pattern))
        return first


# End of file: src/mstair/common/xlogging/logger_util.py
