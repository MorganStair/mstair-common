# File: python/plib_/tokenize_helpers.py
"""
Responsible for parsing Python source code into sections and regions.
"""

from __future__ import annotations

import io
import re
import tokenize
from dataclasses import dataclass, field
from typing import Self

from mstair.common.base.normalize_helpers import normalize_lines
from mstair.common.xdumps.xdumps_api import xdumps
from mstair.common.xlogging.logger_factory import create_logger


@dataclass(kw_only=True, frozen=True)
class CodeRangeBase0:
    """
    Represents a half-open range of lines in a source file.

    This range uses Python-style semantics: [start, end), where
    `start` is the index of the first line included, and `end` is
    the index one past the last included line.

    All indices are 0-based, and the range is valid if 0 <= start <= end.

    For example, a file that starts with a docstring would have no header,
    so the header range would be `CodeLineRange(start=0, end=0)`.
    """

    start: int
    """Start line index (0-based, inclusive). The first line included in the range."""

    end: int
    """End line index (0-based, exclusive). One past the last line included in the range."""

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"Invalid range: start={self.start}, end={self.end}")

    @property
    def length(self) -> int:
        """Number of lines in the range. Returns 0 if the range is empty."""
        return self.end - self.start

    def as_slice(self) -> slice:
        return slice(self.start, self.end)

    def is_empty(self) -> bool:
        """Return True if the range is empty (start == end)."""
        return self.start == self.end


@dataclass(kw_only=True, slots=True)
class CodeRegions:
    """
    Parses Python source code into named regions: header, docstring, body, and footer.

    All region values (lines, columns, and offsets) are 0-based. Each region is exclusive
    at its end position and can be missing if not present in the source.
    """

    header_lines: list[str] = field(default_factory=list[str])
    """Normalized lines in the header region (LF terminated, no leading or trailing blank lines)."""

    docstring_lines: list[str] = field(default_factory=list[str])
    """Normalized lines in the docstring region (LF terminated, no leading or trailing blank lines)."""

    body_lines: list[str] = field(default_factory=list[str])
    """Normalized lines in the body region (LF terminated, no leading or trailing blank lines)."""

    footer_lines: list[str] = field(default_factory=list[str])
    """Normalized lines in the footers region (LF terminated, no leading or trailing blank lines)."""

    def __repr__(self) -> str:
        result = xdumps(self, rshift=4)
        return result

    @classmethod
    def regions_from_code(cls, source_code: str) -> Self:
        """
        Parses Python source code into named regions, using the first "# End of file:" line
        (case-insensitive, ignoring whitespace) as the footers marker.

        Fixed to handle files that start with docstrings (no header comments).

        :param source_code: The complete source code as a string.
        :return: An instance of CodeRegions containing the parsed regions.
        """
        ### Main parsing logic starts here ###
        linesep = "\r\n" if "\r\n" in source_code else "\n"
        lines: list[str] = source_code.splitlines()

        # Handle empty files
        if not lines:
            return cls(
                header_lines=[],
                docstring_lines=[],
                body_lines=[],
                footer_lines=[],
            )

        try:
            first_tok_b1, _ = _first_and_last_code_tokens_base1(source_code=linesep.join(lines))
        except tokenize.TokenError:
            # If tokenization fails, treat entire file as body
            return cls(
                header_lines=[],
                docstring_lines=[],
                body_lines=lines,
                footer_lines=[],
            )

        footer_range_b0: CodeRangeBase0 = CodeRegions._find_footer_range(lines=lines)
        footer_lines = normalize_lines(
            lines[footer_range_b0.as_slice()],
            max_bounding_blanks=(0, 0),
            max_sequential_blanks=0,
        )

        header_end_b0 = (
            min(first_tok_b1.start[0] - 1, footer_range_b0.start) if first_tok_b1 is not None else 0
        )
        header_range_b0: CodeRangeBase0 = CodeRangeBase0(start=0, end=header_end_b0)
        _header_lines = lines[header_range_b0.as_slice()]

        docstring_range_b0: CodeRangeBase0 = CodeRegions._find_docstring_outer_bounds(
            first_tok=first_tok_b1,
            header_range=header_range_b0,
            _lines=lines,
        )
        _docstring_lines = lines[docstring_range_b0.as_slice()]

        # Fix: Ensure body range is valid
        body_start = max(header_range_b0.end, docstring_range_b0.end)
        body_end = min(footer_range_b0.start, len(lines))
        body_start = min(body_start, body_end)

        body_range_b0: CodeRangeBase0 = CodeRangeBase0(
            start=body_start,
            end=body_end,
        )
        _body_lines = lines[body_range_b0.as_slice()]
        _body_lines = normalize_lines(
            lines=_body_lines,
            max_bounding_blanks=(0, 0),
            max_sequential_blanks=2,
        )
        logger = create_logger(__name__)
        logger.trace("_body_lines: %s", _body_lines, color="magenta")

        code_ranges = cls(
            header_lines=_header_lines,
            docstring_lines=_docstring_lines,
            body_lines=_body_lines,
            footer_lines=footer_lines,
        )
        return code_ranges

    @staticmethod
    def _find_docstring_outer_bounds(
        *,
        first_tok: tokenize.TokenInfo | None,
        header_range: CodeRangeBase0,
        _lines: list[str],
    ) -> CodeRangeBase0:
        """
        Determine the complete docstring range including both opening and closing triple quotes.

        This function assumes that the first code token is a triple-quoted string
        and uses its token line numbers to slice out the docstring *including* the quotes.

        :param first_tok: The first code token in the lines, if None there can be no docstring.
        :param header_range: The header range determines where a missing docstring would start.
        :param _lines: The full list of normalized source lines.
        :return: The CodeRange representing the docstring region.
        """
        logger = create_logger(__name__)

        if first_tok is not None and _is_triple_quoted_string(first_tok):
            # TokenInfo.start[0] and end[0] are 1-based line numbers.
            docstring_start_one_based = first_tok.start[0]
            docstring_end_one_based = first_tok.end[0]

            # Convert to 0-based for slicing
            docstring_start_zero_based = docstring_start_one_based - 1
            docstring_end_zero_based = docstring_end_one_based

            # Defensive clamp
            docstring_start_zero_based = max(0, docstring_start_zero_based)
            docstring_end_zero_based = min(len(_lines), docstring_end_zero_based)

            docstring_range = CodeRangeBase0(
                start=docstring_start_zero_based,
                end=docstring_end_zero_based,
            )
        else:
            # No triple-quoted docstring; assume it's empty, between header and body
            docstring_range = CodeRangeBase0(start=header_range.end, end=header_range.end)

        logger.debug(f"{docstring_range=}")
        return docstring_range

    @staticmethod
    def _find_footer_range(
        *,
        lines: list[str],
    ) -> CodeRangeBase0:
        """
        Find the footers range by searching backwards from the end of file.

        :param lines: List of source code lines (0-indexed)
        :return: Range where start is inclusive and end is exclusive (0-based indexing)
        """
        if not lines:
            return CodeRangeBase0(start=0, end=0)

        # Search backwards from the last line
        i = len(lines) - 1
        while i >= 0:
            line = lines[i]
            if not re.search(r"^\s*(?:\s*#.*)?$", line):
                break
            i -= 1
        footer_range = CodeRangeBase0(start=i + 1, end=len(lines))
        return footer_range


def _first_and_last_code_tokens_base1(
    *,
    source_code: str,
) -> tuple[tokenize.TokenInfo | None, tokenize.TokenInfo | None]:
    """
    Find the first and last code tokens in the source code.

    :param source_code: source code to analyze.
    :return tuple[TokenInfo | None, TokenInfo | None]: The first and last code tokens found.
    """
    logger = create_logger(__name__)
    logger.debug(
        "source_code[:100]: %r",
        source_code[:100] if source_code and len(source_code) > 100 else source_code,
    )
    first_code_tok: tokenize.TokenInfo | None = None
    last_code_tok: tokenize.TokenInfo | None = None

    try:
        tokens = tokenize.tokenize(
            io.BytesIO(source_code.encode("utf-8")).readline,
        )
        for _token_count, token in enumerate(tokens):
            if _is_code_token(token):
                if first_code_tok is None:
                    first_code_tok = token
                    last_code_tok = token
                else:
                    last_code_tok = token

    except tokenize.TokenError as e:
        logger.error("Tokenization failed with TokenError: %s", e)
        logger.error("Source code that failed tokenization:\n%s", source_code)
        first_code_tok, last_code_tok = None, None
        pass
    except Exception as e:
        logger.error(
            "Unexpected error during tokenization: %s",
            e,
            exc_info=True,
        )
        logger.error("Source code that caused error:\n%s", source_code)
        first_code_tok, last_code_tok = None, None
        pass

    return first_code_tok, last_code_tok


def _is_code_token(token: tokenize.TokenInfo) -> bool:
    """
    Return True if the token represents syntactic code.

    Filters out non-code tokens like encoding markers, whitespace, structural indentation,
    comments, and tokenizer-specific artifacts. This function is used to isolate tokens
    that correspond to real, user-authored code content including docstrings.

    :param token: A TokenInfo instance from tokenize.tokenize().
    :return: True if the token contributes to code logic.
    """
    NON_CODE_TOKEN_TYPES = (
        tokenize.COMMENT,
        tokenize.DEDENT,
        tokenize.ENCODING,
        tokenize.ENDMARKER,
        tokenize.FSTRING_END,
        tokenize.FSTRING_MIDDLE,
        tokenize.FSTRING_START,
        tokenize.INDENT,
        tokenize.NEWLINE,
        tokenize.NL,
    )
    if token.type in NON_CODE_TOKEN_TYPES:
        return False
    return True


def _is_triple_quoted_string(token: tokenize.TokenInfo) -> bool:
    """
    Check if the token is a triple-quoted string.

    :param token: A TokenInfo instance from tokenize.tokenize().
    :return: True if the token is a triple-quoted string.
    """
    return token.type == tokenize.STRING and (
        token.string.startswith('"""') or token.string.startswith("'''")
    )


# End of file: python/plib_/tokenize_helpers.py
