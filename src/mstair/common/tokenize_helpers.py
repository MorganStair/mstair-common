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
    """Represents a half-open range of lines in a source file."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"Invalid range: start={self.start}, end={self.end}")

    @property
    def length(self) -> int:
        return self.end - self.start

    def as_slice(self) -> slice:
        return slice(self.start, self.end)

    def is_empty(self) -> bool:
        return self.start == self.end


@dataclass(kw_only=True, slots=True)
class CodeRegions:
    """Parses Python source code into named regions."""

    header_lines: list[str] = field(default_factory=list[str])
    docstring_lines: list[str] = field(default_factory=list[str])
    body_lines: list[str] = field(default_factory=list[str])
    footer_lines: list[str] = field(default_factory=list[str])

    def __repr__(self) -> str:
        return xdumps(self, rshift=4)

    @classmethod
    def regions_from_code(cls, source_code: str) -> Self:
        """Parse Python source code into named regions (header, docstring, body, footer)."""
        linesep = "\r\n" if "\r\n" in source_code else "\n"
        lines = source_code.splitlines()

        if not lines:
            return cls()

        try:
            first_tok, _ = _first_and_last_code_tokens_base1(source_code=linesep.join(lines))
        except tokenize.TokenError:
            return cls(body_lines=normalize_lines(lines))

        footer_range = cls._find_footer_range(lines=lines)
        footer_lines = normalize_lines(
            lines[footer_range.as_slice()],
            max_bounding_blanks=(0, 0),
            max_sequential_blanks=0,
        )

        header_range = _compute_header_range(first_tok, footer_range)
        header_lines = lines[header_range.as_slice()]

        docstring_range = cls._find_docstring_outer_bounds(
            first_tok=first_tok, header_range=header_range, _lines=lines
        )
        docstring_lines = lines[docstring_range.as_slice()]

        body_range = _compute_body_range(header_range, docstring_range, footer_range, len(lines))
        body_lines = normalize_lines(
            lines[body_range.as_slice()],
            max_bounding_blanks=(0, 0),
            max_sequential_blanks=2,
        )

        create_logger(__name__).trace("_body_lines: %s", body_lines, color="magenta")

        return cls(
            header_lines=header_lines,
            docstring_lines=docstring_lines,
            body_lines=body_lines,
            footer_lines=footer_lines,
        )

    @staticmethod
    def _find_docstring_outer_bounds(
        *,
        first_tok: tokenize.TokenInfo | None,
        header_range: CodeRangeBase0,
        _lines: list[str],
    ) -> CodeRangeBase0:
        """Determine the complete docstring range including both opening and closing triple quotes."""
        logger = create_logger(__name__)

        if first_tok and _is_triple_quoted_string(first_tok):
            start = max(0, first_tok.start[0] - 1)
            end = min(len(_lines), first_tok.end[0])
            docstring_range = CodeRangeBase0(start=start, end=end)
        else:
            docstring_range = CodeRangeBase0(start=header_range.end, end=header_range.end)

        logger.debug(f"{docstring_range=}")
        return docstring_range

    @staticmethod
    def _find_footer_range(*, lines: list[str]) -> CodeRangeBase0:
        """Find the footers range by searching backwards from the end of file."""
        if not lines:
            return CodeRangeBase0(start=0, end=0)

        i = len(lines) - 1
        while i >= 0:
            line = lines[i]
            if not re.search(r"^\s*(?:\s*#.*)?$", line):
                break
            i -= 1
        return CodeRangeBase0(start=i + 1, end=len(lines))


def _compute_header_range(
    first_tok: tokenize.TokenInfo | None, footer_range: CodeRangeBase0
) -> CodeRangeBase0:
    """Compute the header range from the start of the file to the first token or footer."""
    end = min(first_tok.start[0] - 1, footer_range.start) if first_tok else 0
    return CodeRangeBase0(start=0, end=end)


def _compute_body_range(
    header: CodeRangeBase0, docstring: CodeRangeBase0, footer: CodeRangeBase0, total_lines: int
) -> CodeRangeBase0:
    """Compute the body range between the docstring and footer."""
    start = max(header.end, docstring.end)
    end = min(footer.start, total_lines)
    return CodeRangeBase0(start=min(start, end), end=end)


def _first_and_last_code_tokens_base1(
    *, source_code: str
) -> tuple[tokenize.TokenInfo | None, tokenize.TokenInfo | None]:
    """Find the first and last code tokens in the source code."""
    logger = create_logger(__name__)
    logger.debug(
        "source_code[:100]: %r",
        source_code[:100] if source_code and len(source_code) > 100 else source_code,
    )
    first_tok: tokenize.TokenInfo | None = None
    last_tok: tokenize.TokenInfo | None = None

    try:
        for token in tokenize.tokenize(io.BytesIO(source_code.encode("utf-8")).readline):
            if _is_code_token(token):
                if not first_tok:
                    first_tok = token
                last_tok = token
    except tokenize.TokenError as e:
        logger.error("Tokenization failed: %s", e)
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)

    return first_tok, last_tok


def _is_code_token(token: tokenize.TokenInfo) -> bool:
    """Return True if the token represents syntactic code."""
    return token.type not in {
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
    }


def _is_triple_quoted_string(token: tokenize.TokenInfo) -> bool:
    """Check if the token is a triple-quoted string."""
    return token.type == tokenize.STRING and (
        token.string.startswith('"""') or token.string.startswith("'''")
    )
