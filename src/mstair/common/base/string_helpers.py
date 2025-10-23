import copy
import difflib
import hashlib
import os
import re
import string
import sys
import textwrap
from collections.abc import Iterable
from hashlib import sha256
from pathlib import Path
from typing import Any, Final, TypeAlias

from charset_normalizer import from_bytes


MULTILINE_CONVERSION_NOT_IMPLEMENTED = "This function is not implemented yet."

# Match %-style format specifiers:
#   %s, %d, %f, %r, %x, etc.
#   optionally with mapping keys: %(name)s
#   ignore literal %% (handled separately)
_PRINTF_SPECIFIER_RE: Final[re.Pattern[str]] = re.compile(
    r"""
    %                           # Start of specifier
    (?!%)                       # Not a literal '%%'
    (?:\([^)]+\))?              # Optional mapping key e.g. %(name)
    [#0\- +]?                   # Optional flags
    (?:\d+|\*)?                 # Optional width
    (?:\.(?:\d+|\*))?           # Optional precision
    [hlL]?                      # Optional length modifier (C-style, rarely used)
    [diouxXeEfFgGcrs]           # Conversion type
    """,
    re.VERBOSE,
)

Sanitized: TypeAlias = (
    bool
    | bytes
    | dict[str, "Sanitized"]
    | float
    | int
    | list["Sanitized"]
    | set["Sanitized"]
    | str
    | tuple["Sanitized", ...]
    | None
)


def dedent(text: str) -> str:
    return textwrap.dedent(text.replace("\t", "    "))


def fqn(o: object) -> str:
    return f"{o.__class__.__module__}.{o.__class__.__name__}"


def to_capfirst(s: str) -> str:
    """Capitalize the first character of a string, safely handling empty input."""
    return s[:1].upper() + s[1:]


def to_dict(o: Any) -> dict[Any, Any]:
    assert hasattr(o, "__dict__"), f"Object has no __dict__: {o}"
    _dict = {k: copy.deepcopy(v) for k, v in o.__dict__.items()}
    return _dict


def to_words(*args: str) -> list[str]:
    """Convert text arguments into words without changing case by:
    - Splitting on non-alphanumeric characters.
    - Splitting at uppercase-to-lowercase or digit transitions.
    - Treating digits as lowercase.

    Args:
        *args (str): Input strings to split into words.

    Returns:
        list[str]: list of words.

    """
    words: list[str] = []
    for text in args:
        # Extract sequences of alphanumeric characters
        alphanumeric_parts = re.findall(r"[A-Za-z0-9]+", text)
        for part in alphanumeric_parts:
            # Split based on transitions between uppercase and lowercase/digits
            split_parts = re.findall(r"[A-Z]{2,}(?=[A-Z][a-z0-9])|[A-Z][a-z0-9]*|[a-z0-9]+", part)

            # Add the split parts to words list
            words.extend(split_parts)

    return words


def to_header_case(name: str) -> str:
    words = to_words(name)
    return "-".join(word.capitalize() for word in words)


def to_header_cases(names: list[str]) -> list[str]:
    return sorted({to_header_case(name) for name in names})


def to_kabob_case(text: str) -> str:
    """Convert text into a "kabob-case-text" string."""
    words = to_words(text)
    kabob_case = "-".join(words).lower()
    return kabob_case


def get_cache_key(value: Any) -> str:
    """Generate a cache key from a raw object of any type."""
    if not isinstance(value, str):
        value = repr(value)
    return sha256(value.encode("utf-8")).hexdigest()


def maybe_truncate(text: str, max_len: int) -> str:
    """Truncate the text if it exceeds the maximum length."""
    if len(text) > max_len:
        text = text[: max_len - 15] + "... [TRUNCATED]"
    return text


def to_title_text(text: str) -> str:
    """Convert text into a space separated "Title Case Text" string."""
    words = to_words(text)
    title_text = " ".join(word.capitalize() for word in words)
    return title_text


def to_pascal_case(text: str) -> str:
    """Convert text into a "PascalCaseText" string."""
    words = to_words(text)
    result = "".join(word.capitalize() for word in words)
    return result


def to_snake_case(text: str) -> str:
    """Convert text into a "snake_case_text" string."""
    words = to_words(text)
    snake_case = "_".join(words).lower()
    return snake_case


def to_snake_cases(texts: list[str]) -> list[str]:
    return sorted({to_snake_case(text) for text in texts})


def safe_decode_chunk(chunk: bytes) -> str:
    try:
        _detection = from_bytes(chunk).best()
        if _detection:
            detected_encoding = _detection.encoding
            _decoded_chunk = chunk.decode(detected_encoding)
        else:
            _decoded_chunk = chunk.decode("utf-8")
    except UnicodeDecodeError:
        _decoded_chunk = chunk.decode("latin1", errors="replace")
    return _decoded_chunk


def script_name() -> str:
    """Return the script name of the current module.

    :return: The script name without the file extension.
    """
    script_path = sys.argv[0]
    script_name = os.path.splitext(os.path.basename(script_path))[0]
    return script_name


def split_phrases(text: str) -> list[str]:
    """Split a message into individual phrases.

    Phrases are detected based on the presence of sentence-ending punctuation followed by spaces, newlines, or
    the end of the string. This function removes leading punctuation and filters out meaningless standalone
    periods.

    :param text: The commit message text.
    :return: A list of strings representing individual phrases.
    """
    # Define the pattern to capture phrases, using non-capturing groups for better legibility.
    _pattern: str = r"(?:^|(?<=\n))[^a-zA-Z0-9]* *"  # Match the start of a line or leading punctuation with spaces.
    _pattern += r"([^.\n]+(?:\.[^.\n]*)*)"  # Capture non-period phrases optionally followed by trailing text.
    _pattern += (
        r"(?=\. *(?:\n|$)|\n|$)"  # Ensure phrases end at periods followed by newline or end of text.
    )

    # Extract phrases using the pattern
    _phrases = [
        phrase.strip("- ").strip() for phrase in re.findall(_pattern, text) if phrase.strip()
    ]

    return _phrases


def trim(text: str, max_length: int) -> str:
    """Trim the text to the specified maximum length."""
    if max_length > 0 and len(text) > max_length:
        return text[:max_length] + "..."
    return text


def strip_bounding_blank_lines(text: list[str] | str) -> str:
    """
    Remove leading and trailing blank lines but preserve internal structure and line endings.

    :param text: A multi-line string possibly wrapped in blank lines.
    :return: The same text without blank lines at the start or end.
    """
    lines = text if isinstance(text, list) else (text + "\n").splitlines(keepends=True)

    # Remove only completely blank leading lines
    start = 0
    while start < len(lines) and lines[start].strip() == "":
        start += 1

    # Remove only completely blank trailing lines
    end = len(lines)
    while end > start and lines[end - 1].strip() == "":
        end -= 1

    return "".join(lines[start:end])


def count_printf_specifiers(format_string: str) -> int:
    """
    Count the number of format specifiers in a %-format string.

    Examples:
        "x=%s y=%d"   -> 2
        "%% done %s"  -> 1   (%% does not count)

    :param format_string: A %-style format string.
    :return: The number of format specifiers.
    """
    try:
        return len(_PRINTF_SPECIFIER_RE.findall(format_string))
    except re.error:
        return 0


def count_format_specifiers(format_string: str) -> int:
    """
    Count the number of format specifiers in a str.format()-style string.

    Example:
        "a{}b{0}c{x}" -> 3

    This deliberately ignores literal text and escaped braces.

    :param format_string: The format string to analyze.
    :return: Number of format specifiers.
    """
    try:
        text_spans: Iterable[tuple[str, str | None, str | None, str | None]]
        text_spans = string.Formatter().parse(format_string)

        count: int = 0
        for _literal_text, field_name, _format_spec, _conversion in text_spans:
            if not field_name:
                continue
            count += 1
        return count
    except ValueError:
        # Bad format string, treat as having no specifiers
        return 0


def udiff(
    original: str,
    revised: str,
    filename: str | Path = "",
    n: int = 3,
) -> list[str]:
    """Generate unified diff lines between two strings."""
    return list(
        difflib.unified_diff(
            a=original.splitlines(),
            b=revised.splitlines(),
            fromfile=str(filename),
            tofile=str(filename),
            n=n,
        )
    )


def text_checksum(text: str, num_chars: int = 4, long: bool = True) -> str:
    """Generate a short checksum that's position-independent."""
    numlines = len(text.splitlines())
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()
    if num_chars > 0 and num_chars < len(digest):
        digest = digest[:num_chars]
    if long:
        return f"({numlines=},{digest=})"
    else:
        return digest


def text_truncate(
    text: str,
    *,
    max_lines: int = 0,
    max_chars: int = 0,
) -> str:
    """
    Truncate text to a maximum number of lines or characters (not both), adding an ellipsis if needed.
    """
    invalid_args = (
        max_lines < 0
        or max_chars < 0
        or (max_lines > 0 and max_chars > 0)
        or (max_lines == 0 and max_chars == 0)
    )
    if invalid_args:
        raise RuntimeError("Specify only one of max_lines or max_chars with a positive value")

    linesep = "\r\n" if "\r\n" in text else "\n"
    result: str = text
    if max_chars > 0:
        if len(text) > max_chars:
            result = text[:max_chars].strip() + "...truncated..."
    elif max_lines > 0:
        _lines = text.splitlines()
        if len(_lines) > max_lines:
            _lines = [*_lines[:max_lines], "...truncated..."]
            result = linesep.join(_lines)
    return result
