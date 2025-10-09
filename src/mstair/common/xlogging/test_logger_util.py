# File: tests/test_logger_util.py
"""
Tests for LogLevelConfig: parsing, overrides, matching, and lifecycle.

Covers:
- DSL parsing from LOG_LEVEL / LOG_LEVELS
- Per-logger overrides from LOG_LEVEL_* variables
- Precedence rules and matching semantics
- Singleton and reload behavior
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator

import pytest

from mstair.common.xlogging import logger_util as lu
from mstair.common.xlogging.logger_util import LogLevelConfig


# ---------- Fixtures ----------


@pytest.fixture(autouse=False)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Clear LOG_LEVEL* vars and reset singleton around each test, skipping .env loads."""
    # Prevent .env file from being read
    monkeypatch.setattr(lu, "fs_load_dotenv", lambda *a, **k: False)

    keys_to_delete = [k for k in os.environ if k.startswith("LOG_LEVEL")]
    for k in keys_to_delete:
        monkeypatch.delenv(k, raising=False)

    monkeypatch.setattr(lu, "_log_level_config_instance", None, raising=False)

    yield

    for k in keys_to_delete:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(lu, "_log_level_config_instance", None, raising=False)


# ---------- Parsing: DSL in LOG_LEVELS ----------


class TestEnvironmentParsingDSL:
    def test_simple_global_bare_level(
        self, monkeypatch: pytest.MonkeyPatch, clean_env: None
    ) -> None:
        monkeypatch.setenv("LOG_LEVELS", "DEBUG")
        cfg = LogLevelConfig()
        assert cfg.get_effective_level("any.module") == logging.DEBUG

    def test_pattern_colon_separator(self, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
        monkeypatch.setenv("LOG_LEVELS", "myapp.*:DEBUG")
        cfg = LogLevelConfig()
        assert cfg.pattern_to_level["myapp.*"] == logging.DEBUG
        assert cfg.get_effective_level("myapp.core") == logging.DEBUG

    def test_pattern_equals_separator(
        self, monkeypatch: pytest.MonkeyPatch, clean_env: None
    ) -> None:
        monkeypatch.setenv("LOG_LEVELS", "myapp.*=DEBUG")
        cfg = LogLevelConfig()
        assert cfg.pattern_to_level["myapp.*"] == logging.DEBUG

    @pytest.mark.parametrize(
        "value",
        ["pkg1.*:DEBUG;pkg2.*:INFO", "pkg1.*:DEBUG,pkg2.*:INFO", "pkg1.*:DEBUG pkg2.*:INFO"],
    )
    def test_multiple_patterns_various_separators(
        self, monkeypatch: pytest.MonkeyPatch, clean_env: None, value: str
    ) -> None:
        monkeypatch.setenv("LOG_LEVELS", value)
        cfg = LogLevelConfig()
        assert cfg.pattern_to_level["pkg1.*"] == logging.DEBUG
        assert cfg.pattern_to_level["pkg2.*"] == logging.INFO

    def test_mixed_separators_and_whitespace(
        self, monkeypatch: pytest.MonkeyPatch, clean_env: None
    ) -> None:
        monkeypatch.setenv("LOG_LEVELS", "a:DEBUG; b:INFO, c:WARNING d:ERROR")
        cfg = LogLevelConfig()
        assert len(cfg.pattern_to_level) == 4
        assert cfg.pattern_to_level["a"] == logging.DEBUG
        assert cfg.pattern_to_level["d"] == logging.ERROR

    def test_quoted_values(self, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
        monkeypatch.setenv("LOG_LEVELS", '"pkg.*":"DEBUG"')
        cfg = LogLevelConfig()
        assert cfg.pattern_to_level["pkg.*"] == logging.DEBUG

    def test_empty_env_ignored(self, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
        monkeypatch.setenv("LOG_LEVELS", "")
        cfg = LogLevelConfig()
        assert len(cfg.pattern_to_level) == 0

    def test_root_alias_in_dsl_sets_default(
        self, monkeypatch: pytest.MonkeyPatch, clean_env: None
    ) -> None:
        monkeypatch.setenv("LOG_LEVELS", "root=WARNING; myapp=INFO")
        cfg = LogLevelConfig()
        assert cfg.get_effective_level("myapp.module") == logging.INFO
        assert cfg.get_effective_level("other.module") == logging.WARNING


# ---------- Parsing: LOG_LEVEL and LOG_LEVEL_* overrides ----------


class TestEnvironmentParsingPerLogger:
    def test_simple_global_in_LOG_LEVEL(
        self, monkeypatch: pytest.MonkeyPatch, clean_env: None
    ) -> None:
        monkeypatch.setenv("LOG_LEVEL", "INFO")
        cfg = LogLevelConfig()
        assert cfg.get_effective_level("x.y") == logging.INFO

    def test_LOG_LEVEL_ROOT_sets_default(
        self, monkeypatch: pytest.MonkeyPatch, clean_env: None
    ) -> None:
        monkeypatch.setenv("LOG_LEVEL_ROOT", "ERROR")
        cfg = LogLevelConfig()
        assert cfg.get_effective_level("unmatched") == logging.ERROR

    def test_per_logger_override_exact(
        self, monkeypatch: pytest.MonkeyPatch, clean_env: None
    ) -> None:
        monkeypatch.setenv("LOG_LEVELS", "myapp.*:DEBUG")
        monkeypatch.setenv("LOG_LEVEL_MYAPP_CORE", "ERROR")
        cfg = LogLevelConfig()
        assert cfg.get_effective_level("myapp.core") == logging.ERROR
        assert cfg.get_effective_level("myapp.util") == logging.DEBUG

    def test_per_logger_escape_double_underscore(
        self, monkeypatch: pytest.MonkeyPatch, clean_env: None
    ) -> None:
        monkeypatch.setenv("LOG_LEVEL_MYAPP__CORE", "DEBUG")  # -> myapp_core
        cfg = LogLevelConfig()
        assert cfg.get_effective_level("myapp_core") == logging.DEBUG
        assert cfg.get_effective_level("myapp.core") == logging.WARNING


# ---------- Matching semantics ----------


class TestMatchingSemantics:
    def test_exact_match(self, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
        monkeypatch.setenv("LOG_LEVELS", "myapp.core:DEBUG")
        cfg = LogLevelConfig()
        assert cfg.get_effective_level("myapp.core") == logging.DEBUG
        assert cfg.get_effective_level("myapp.util") == logging.WARNING

    def test_star_glob(self, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
        monkeypatch.setenv("LOG_LEVELS", "myapp.*:DEBUG")
        cfg = LogLevelConfig()
        assert cfg.get_effective_level("myapp.util.helpers") == logging.DEBUG
        assert cfg.get_effective_level("other") == logging.WARNING

    def test_question_glob(self, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
        monkeypatch.setenv("LOG_LEVELS", "pkg?:DEBUG")
        cfg = LogLevelConfig()
        assert cfg.get_effective_level("pkg1") == logging.DEBUG
        assert cfg.get_effective_level("pkg12") == logging.WARNING

    def test_bracket_glob(self, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
        monkeypatch.setenv("LOG_LEVELS", "pkg[123]:DEBUG")
        cfg = LogLevelConfig()
        assert cfg.get_effective_level("pkg2") == logging.DEBUG
        assert cfg.get_effective_level("pkg9") == logging.WARNING

    def test_case_insensitive(self, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
        monkeypatch.setenv("LOG_LEVELS", "MyApp.*:DEBUG")
        cfg = LogLevelConfig()
        assert cfg.get_effective_level("myapp.core") == logging.DEBUG
        assert cfg.get_effective_level("MYAPP.UTIL") == logging.DEBUG

    def test_specific_beats_glob(self, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
        monkeypatch.setenv("LOG_LEVELS", "myapp.*:DEBUG;myapp.core:ERROR")
        cfg = LogLevelConfig()
        assert cfg.get_effective_level("myapp.core") == logging.ERROR

    def test_ancestor_beats_glob(self, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
        monkeypatch.setenv("LOG_LEVELS", "myapp.*:DEBUG; myapp.core:ERROR")
        cfg = LogLevelConfig()
        assert cfg.get_effective_level("myapp.core.utils") == logging.ERROR

    def test_glob_tie_break_longest_fixed_prefix(
        self, monkeypatch: pytest.MonkeyPatch, clean_env: None
    ) -> None:
        monkeypatch.setenv("LOG_LEVELS", "my*:DEBUG; myapp*:INFO")
        cfg = LogLevelConfig()
        assert cfg.get_effective_level("myapp.module") == logging.INFO

    def test_default_is_not_matched_as_pattern(
        self, monkeypatch: pytest.MonkeyPatch, clean_env: None
    ) -> None:
        monkeypatch.setenv("LOG_LEVELS", "INFO; m*:DEBUG")
        cfg = LogLevelConfig()
        assert cfg.get_effective_level("misc") == logging.DEBUG
        assert cfg.get_effective_level("zzz") == logging.INFO


# ---------- Lifecycle ----------


class TestLifecycle:
    def test_update_resets_state(self, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
        monkeypatch.setenv("LOG_LEVEL", "pkg1.*:DEBUG")
        cfg = LogLevelConfig()
        assert "pkg1.*" in cfg.pattern_to_level

        monkeypatch.setenv("LOG_LEVEL", "pkg2.*:INFO")
        cfg.update_from_environment()
        assert "pkg1.*" not in cfg.pattern_to_level
        assert "pkg2.*" in cfg.pattern_to_level

    def test_singleton_get_instance(self, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
        monkeypatch.setenv("LOG_LEVEL", "INFO")
        cfg1 = LogLevelConfig.get_instance()
        assert cfg1.get_effective_level("x") == logging.INFO

        monkeypatch.setenv("LOG_LEVEL", "ERROR")
        cfg2 = LogLevelConfig.get_instance()
        assert cfg1 is cfg2
        assert cfg2.get_effective_level("x") == logging.INFO

        cfg2.update_from_environment()
        assert cfg2.get_effective_level("x") == logging.ERROR


# ---------- Edge cases ----------


class TestEdgeCases:
    def test_numeric_level_ignored(self, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
        monkeypatch.setenv("LOG_LEVEL", "10")
        cfg = LogLevelConfig()
        assert cfg.get_effective_level("x") == logging.WARNING

    def test_custom_level_names_supported(
        self, monkeypatch: pytest.MonkeyPatch, clean_env: None
    ) -> None:
        logging.addLevelName(25, "CUSTOM")
        monkeypatch.setenv("LOG_LEVEL", "CUSTOM")
        cfg = LogLevelConfig()
        assert cfg.get_effective_level("x") == 25

    def test_unicode_patterns(self, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
        monkeypatch.setenv("LOG_LEVELS", "module.*:DEBUG")
        cfg = LogLevelConfig()
        assert cfg.get_effective_level("module.core") == logging.DEBUG

    def test_multiple_assignment_splits_once(
        self, monkeypatch: pytest.MonkeyPatch, clean_env: None
    ) -> None:
        monkeypatch.setenv("LOG_LEVELS", "pattern:DEBUG:extra")
        cfg = LogLevelConfig()
        assert len(cfg.pattern_to_level) == 0

    def test_empty_fragments_skipped(self, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
        monkeypatch.setenv("LOG_LEVELS", ";;pkg.*:DEBUG;;")
        cfg = LogLevelConfig()
        assert list(cfg.pattern_to_level.keys()) == ["pkg.*"]


# End of file: src/mstair/common/xlogging/test_logger_util.py
