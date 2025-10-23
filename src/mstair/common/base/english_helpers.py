"""
Text Helpers Module

This module provides functions to clean up and process text messages.
"""

import re


def english_cleanup_line(line: str) -> str:
    """
    Clean up a single line of text.
    - Removes leading non-alphanumeric characters.
    - Replaces multiple spaces with a single space.
    - Strips trailing whitespace.
    - Checks for corruption in the line.
    """
    english_runon_paragraph_check(line)
    line = re.sub(r"^[^a-zA-Z0-9]+", "", line)
    line = re.sub(r"\s+", " ", line)
    line = line.rstrip()
    english_runon_paragraph_check(line)
    return line


def english_paragraph_cleanup(
    text: str | bytes | list[str] | list[str | bytes], *, max_length: int = 0
) -> str:
    """
    Use string functions to clean up a message and truncate it if necessary.
    - Converts bytes to UTF-8 string if necessary.
    - Removes empty or None messages.
    - Joins lines with '. ' and cleans each line with `cleanup_english_line()`.
    - Replaces sequences of periods and spaces like '..', '.  .', etc., with a single '.'.
    - Strips leading and trailing whitespace.
    - Truncates the message to `max_length`, appending '...' if trimmed.
    Args:
        message (str | bytes | list[str] | list[str|bytes]): The input message(s) to combine.
        max_length (int): Maximum length of the output. If <= 3, no truncation is applied.
    Returns:
        str: The cleaned, optionally truncated, message.
    Raises:
        TypeError: If message is a list of single-character strings, which likely indicates a misuse.
    """

    def _cleanup_nonlist(message: str | bytes, max_length: int) -> str:
        if not message:
            return ""
        assert isinstance(message, str | bytes)
        _message1 = message if isinstance(message, str) else message.decode("utf-8")
        # Workaround python bug (search https://bugs.python.org)
        # _message = ". ".join(cleanup_line(_line) for _line in _message.splitlines())
        _lines = _message1.splitlines()
        _lines = [english_cleanup_line(_line) for _line in _lines]
        _message2 = ". ".join(_lines)
        english_runon_paragraph_check(_message2)
        # Replace sequences of periods and spaces with a single period
        _message2 = re.sub(r"\.+[\s\.]*\.+", ".", _message2)
        # Replace ":." with ":"
        _message2 = re.sub(r":\.+", r"\:", _message2)
        _message2 = _message2.strip()
        if max_length > 3 and len(_message2) > max_length:
            _message2 = _message2[: max_length - 3] + "..."
        return english_runon_paragraph_check(_message2)

    if isinstance(text, list):
        if all(isinstance(m, str) and len(m) == 1 for m in text):
            raise TypeError("Invalid message: list of single-character strings.")
        if not all(isinstance(m, str | bytes) for m in text):
            raise TypeError("Invalid message: all elements must be str or bytes.")
        _message = "\n".join(_cleanup_nonlist(m, max_length) for m in text if m)
        english_runon_paragraph_check(_message)
    else:
        _message = _cleanup_nonlist(text, max_length)
        english_runon_paragraph_check(_message)
    return english_runon_paragraph_check(_message)


def english_runon_paragraph_check(text: str) -> str:
    """
    Check for corruption in the text.
    - Raises RuntimeError if the text contains more than 5 consecutive sentences.
    - This is a heuristic to detect potential bugs in user content.
    """
    if bool(re.search(r"(?:\w\.\s){5,}", text)):
        raise RuntimeError("Bug detected in user content.")
    return text
