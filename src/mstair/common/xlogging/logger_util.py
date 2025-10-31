"""
Environment variable-driven log level configuration.

Two sources are supported:
- Pattern-based DSL strings in LOG_LEVEL / LOG_LEVELS
- Per-logger overrides in variables like LOG_LEVEL_<NAME>

This module resolves the desired level for a given logger name; it does not
modify or infer the root logger's level. CoreLogger ensures the effective
emission is at least the root's level. To lower the global threshold, call
initialize_root(level=...) from mstair.common.xlogging.core_logger.

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


def _normalize_app_token(name: str) -> str:
    """Return an uppercase token suitable for env var suffix from an app name.

    Non-alphanumeric characters are converted to underscores and repeated
    underscores are collapsed.
    """
    token = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    token = re.sub(r"_+", "_", token)
    return token.upper()


def _level_from_text(txt: str, level_map: dict[str, int]) -> int | None:
    """Return numeric level from a name or decimal number string, else None."""
    s = txt.strip().strip("\"'")
    if not s:
        return None
    if s.isdigit():
        try:
            return int(s, 10)
        except ValueError:
            return None
    lvl = level_map.get(s.upper())
    if isinstance(lvl, int) and lvl != logging.NOTSET:
        return lvl
    return None


def _glob_specificity_local(pattern: str) -> int:
    """Length of fixed prefix before any wildcard (for glob tiebreaks)."""
    first = min((i for i, ch in enumerate(pattern) if ch in "*?["), default=len(pattern))
    return first


def _parse_root_levels_dsl(
    dsl: str, level_map: dict[str, int]
) -> tuple[list[tuple[str, int]], int | None]:
    """Parse LOG_ROOT_LEVELS DSL into (patterns, default_level)."""
    patterns: list[tuple[str, int]] = []
    default_level: int | None = None
    for fragment in _LOG_VAR_FRAGMENT_SEPARATOR_RX.split(dsl):
        part = fragment.strip()
        if not part:
            continue
        segs = _LOG_VAR_ASSIGNMENT_OPERATOR_RX.split(part, maxsplit=1)
        if len(segs) == 2:
            pat = segs[0].strip().strip("'\"")
            level_txt = segs[1].strip().strip("'\"")
        else:
            pat = ""
            level_txt = segs[0].strip().strip("'\"")
        lvl_val = _level_from_text(level_txt, level_map)
        if lvl_val is None:
            continue
        if pat:
            patterns.append((pat, lvl_val))
        else:
            default_level = lvl_val
    return patterns, default_level


def _match_app_level(
    app_name: str, patterns: list[tuple[str, int]], default_level: int | None
) -> int | None:
    """Return level for app_name using exact first, then best glob, else default."""
    app_lc = app_name.lower()
    for pat, lvl_val in patterns:
        if pat.lower() == app_lc:
            return lvl_val
    best: tuple[int, int] | None = None
    for pat, lvl_val in patterns:
        pl = pat.lower()
        if fnmatch.fnmatch(app_lc, pl):
            score = _glob_specificity_local(pl)
            if best is None or score > best[0]:
                best = (score, lvl_val)
    if best is not None:
        return best[1]
    return default_level


def get_root_level_from_environment(app_name: str | None = None) -> int | None:
    """Return a root logger level from environment if defined.

    Precedence (first match wins):
    1. LOG_ROOT_LEVEL_<APP>
    2. LOG_ROOT_LEVEL

    Where <APP> is derived from ``app_name`` by uppercasing and converting any
    non-alphanumeric characters to underscores.

    Returns None if no valid level is configured.
    """
    fs_load_dotenv()
    # Build mapping once that includes custom levels (TRACE, CONSTRUCT, ...)
    initialize_logger_constants()
    level_map: dict[str, int] = {
        k.upper(): v
        for k, v in logging.getLevelNamesMapping().items()
        if isinstance(k, str) and k.isupper() and isinstance(v, int)
    }

    # 1) Per-app explicit override
    if app_name:
        app_var = f"LOG_ROOT_LEVEL_{_normalize_app_token(app_name)}"
        raw = os.environ.get(app_var)
        if raw:
            lvl = _level_from_text(raw, level_map)
            if lvl is not None:
                return lvl

    # 2) DSL-based mapping for app names, same separators and operators as LOG_LEVELS
    dsl = os.environ.get("LOG_ROOT_LEVELS", "")
    if dsl:
        patterns, default_level = _parse_root_levels_dsl(dsl, level_map)
        if app_name:
            lvl = _match_app_level(app_name, patterns, default_level)
            if lvl is not None:
                return lvl
        elif default_level is not None:
            return default_level

    # 3) Global single value fallback
    raw_global = os.environ.get("LOG_ROOT_LEVEL")
    if raw_global:
        lvl = _level_from_text(raw_global, level_map)
        if lvl is not None:
            return lvl
    return None


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
                if pattern not in {"", "root"}:
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
