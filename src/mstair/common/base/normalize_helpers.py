"""
Helpers for Normalizing Text Lines

Provides functions to normalize text lines by removing bounding blanks, sequential blanks,
triple quotes, and trailing spaces. Useful for preparing text for further processing or
comparison.
"""

import re
from typing import NamedTuple


__all__ = [
    "normalize_lines",
    "MaxBoundingBlanks",
    "normalize_bounding_blanks",
    "normalize_sequential_blanks",
    "normalize_rstrip_lines",
    "normalize_triple_quotes",
]


class MaxBoundingBlanks(NamedTuple):
    leading: int = 0
    trailing: int = 0


def normalize_lines(
    lines: list[str] | str,
    *,
    strip_triple_quotes: bool = False,
    max_bounding_blanks: MaxBoundingBlanks | tuple[int, int] = (-1, -1),
    max_sequential_blanks: int = -1,
    strip_leading: re.Pattern[str] | str = "",
) -> list[str]:
    """
    Normalize lines by stripping line endings (always) then applying various transformations.

    By default, only converts the `lines` into a list and strips trailing spaces.

    :param lines: List of lines to normalize.
    :param strip_triple_quotes: Whether to remove triple quotes around the lines, default is False.
    :param max_empty_bounds: Max leading and trailing blank lines, -1 means no limit, default is (-1, -1).
    :param max_sequential_blanks: Max sequential blank lines, -1 means no limit, default is -1.
    :param strip_leading: Text or pattern to strip from the start of every line, "" means strip nothing, default is "".
    :return: Normalized lines with the specified transformations applied.
    """
    lines = [_l.rstrip() for _l in (lines if isinstance(lines, list) else lines.splitlines())]
    if not lines:
        return lines
    # Note: order matters
    lines = normalize_triple_quotes(lines=lines, strip_triple_quotes=strip_triple_quotes)
    lines = normalize_bounding_blanks(lines=lines, max_bounding_blanks=max_bounding_blanks)
    lines = normalize_sequential_blanks(lines=lines, max_sequential_blanks=max_sequential_blanks)
    lines = normalize_rstrip_lines(lines=lines, leading_pattern=strip_leading)
    return lines


def normalize_bounding_blanks(
    *,
    lines: list[str],
    max_bounding_blanks: MaxBoundingBlanks | tuple[int, int] = (0, 0),
) -> list[str]:
    """
    Limit the number of leading and trailing blank lines in the provided list of lines.

    :param lines: List of lines to normalize.
    :param max_bounding_blanks: Max leading and trailing empty lines, (-1,-1) means no limit, default is (0, 0).
    :return: Lines with bounding blanks normalized.
    """
    max_blanks: MaxBoundingBlanks = MaxBoundingBlanks(*max_bounding_blanks)

    # Trim leading blank lines
    if max_blanks.leading >= 0:
        leading_blank_count = next(
            (idx for idx, line in enumerate(lines) if line.strip()),
            len(lines),
        )
        start = leading_blank_count - max_blanks.leading
        if start > 0:
            lines = lines[start:]

    # Trim trailing blank lines
    if max_blanks.trailing >= 0:
        trailing_blank_count = next(
            (idx for idx, line in enumerate(reversed(lines)) if line.strip()),
            len(lines),
        )
        remove = trailing_blank_count - max_blanks.trailing
        if remove > 0:
            lines = lines[:-remove]

    return lines


def normalize_triple_quotes(
    *,
    lines: list[str],
    strip_triple_quotes: bool = True,
) -> list[str]:
    """
    Remove triple quotes from the start and end of the lines if present.
    Handles all variations of triple quotes (double and single) including mixed types.
    """
    if not strip_triple_quotes or not lines:
        return lines

    stripped_lines = normalize_bounding_blanks(
        lines=lines, max_bounding_blanks=MaxBoundingBlanks(0, 0)
    )

    # Handle single line case
    if len(stripped_lines) == 1:
        line = stripped_lines[0].strip()
        # Check for any triple quote start and end combination
        starts_with_triple = line.startswith('"""') or line.startswith("'''")
        ends_with_triple = line.endswith('"""') or line.endswith("'''")

        if starts_with_triple and ends_with_triple and len(line) >= 6:
            # Remove the first 3 and last 3 characters (the triple quotes)
            inner_content = line[3:-3]
            return [inner_content]

    # Handle multi-line case
    if len(stripped_lines) >= 2:
        start_line = stripped_lines[0].strip()
        end_line = stripped_lines[-1].strip()

        # Check if first line starts with triple quotes
        starts_with_triple = start_line.startswith('"""') or start_line.startswith("'''")
        # Check if last line ends with triple quotes
        ends_with_triple = end_line.endswith('"""') or end_line.endswith("'''")

        if starts_with_triple and ends_with_triple:
            result: list[str] = []

            # Handle first line - remove opening quotes and keep any remaining content
            first_content = start_line[3:].rstrip()
            if first_content:  # If there's content after opening quotes
                result.append(first_content)

            # Add middle lines unchanged
            result.extend(stripped_lines[1:-1])

            # Handle last line - remove closing quotes and keep any preceding content
            last_content = end_line[:-3].lstrip()
            if last_content:  # If there's content before closing quotes
                result.append(last_content)

            return result

    return lines


def normalize_sequential_blanks(
    *,
    lines: list[str],
    max_sequential_blanks: int,
) -> list[str]:
    """
    Remove sequential blank lines exceeding the specified maximum.
    """
    if max_sequential_blanks < 0:
        return lines
    lines = lines.copy()
    result: list[str] = []
    blank_count = 0
    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count > max_sequential_blanks:
                continue
        else:
            blank_count = 0
        result.append(line)
    return result


def normalize_rstrip_lines(
    *,
    lines: list[str],
    leading_pattern: re.Pattern[str] | str = "",
) -> list[str]:
    """
    Remove leading characters from each line based on the provided pattern or string.

    :param lines: List of lines to normalize.
    :param leading_pattern: Pattern to strip from the start of every line, "" means strip nothing, default is "".
    :return: Lines with leading characters stripped.
    """
    if isinstance(leading_pattern, re.Pattern):
        lines = [re.sub(leading_pattern, "", line) for line in lines]
    elif leading_pattern != "":
        lines = [
            _l[len(leading_pattern) :] if _l.startswith(leading_pattern) else _l for _l in lines
        ]

    return lines
