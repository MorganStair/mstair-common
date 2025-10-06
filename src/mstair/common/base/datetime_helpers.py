# File: python/plib_/base/datetime_helpers.py
"""
timezone and tzinfo helpers
"""

from __future__ import annotations

import ctypes
import datetime
from typing import Literal


def local_tzinfo() -> datetime.tzinfo:
    """
    Get the local timezone info, guaranteed not to be None.

    :return datetime.tzinfo: Local timezone info for the current system.
    :raises RuntimeError: If the local timezone cannot be determined.
    """
    # Attempt 1: Naive local time
    tzinfo: datetime.tzinfo | None = datetime.datetime.now().astimezone().tzinfo
    if tzinfo is not None:
        return tzinfo

    # Attempt 2: Local time via UTC context
    tzinfo = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
    if tzinfo is not None:
        return tzinfo

    # Attempt 3: Fallback to system UTC
    tzinfo = utc_timezone()
    return tzinfo


def local_timezone() -> datetime.timezone:
    """
    Get the local timezone.

    :return: Local timezone.
    """
    tzinfo = local_tzinfo()
    if not isinstance(tzinfo, datetime.timezone):
        tzoffset: datetime.timedelta | None = tzinfo.utcoffset(None)
        if not tzoffset:
            raise ValueError("Unable to determine local timezone offset.")
        tzinfo = datetime.timezone(tzoffset)
    return tzinfo


def utc_timezone() -> datetime.timezone:
    """
    Get the UTC timezone.

    :return timezone: UTC timezone.
    """
    return datetime.timezone.utc


################################################################################
# Current time helpers
################################################################################


def now_localtime(tz: datetime.timezone | None = None) -> datetime.datetime:
    """
    Get the current local datetime.

    :return: Current local datetime.
    """
    return datetime.datetime.now(tz=tz)


def now_utc() -> datetime.datetime:
    """
    Get the current UTC datetime.

    :return: Current UTC datetime.
    """
    return datetime.datetime.now(tz=datetime.timezone.utc)


################################################################################
# Time formatting and conversion helpers
################################################################################


def datetime_from_isoformat(
    iso8601_string: str,
    *,
    default: datetime.datetime = datetime.datetime.min,
) -> datetime.datetime:
    """
    Convert an ISO 8601 string to a datetime object.
    If the string is None or empty, return the default datetime.

    :param iso8601_string: The ISO 8601 string to convert.
    :param default: The default datetime to return if the string is None or empty.
    :return: A datetime object.
    """
    try:
        return datetime.datetime.fromisoformat(iso8601_string)
    except ValueError:
        return default


def msoffice_datetime_format_from_win32(dotnet_format: str) -> str:
    """
    Convert a .NET format string to an Office-compatible format string.
    This function replaces .NET-specific format specifiers with their Office equivalents.

    :param dotnet_format: The .NET format string.
    :return str: The Office-compatible format string.
    """
    return (
        dotnet_format.replace("tt", "AM/PM")
        .replace("yyyy", "yyyy")
        .replace("yy", "yy")
        .replace("MMMM", "mmmm")
        .replace("MMM", "mmm")
        .replace("MM", "mm")
        .replace("M", "m")
        .replace("dddd", "dddd")
        .replace("ddd", "ddd")
        .replace("dd", "dd")
        .replace("d", "d")
        .replace("HH", "hh")  # 24-hour
        .replace("H", "h")
        .replace("hh", "hh")  # 12-hour
        .replace("h", "h")
        .replace("mm", "mm")
        .replace("ss", "ss")
        .replace("fff", "ms")  # milliseconds
    )


def msoffice_datetime_format(*, kind: Literal["date", "time", "datetime"]) -> str:
    """
    Return an openpyxl-compatible number format string based on the current Windows locale.

    :param return: "date", "time", or "datetime".
    :return: A string representing the datetime format compatible with Microsoft Office.
    """
    LOCALE_SSHORTDATE = 0x1F  # Code for the user's short date format, e.g., "dd/MM/yyyy"
    LOCALE_STIMEFORMAT = 0x1003  # Code for the user's time format, e.g., "HH:mm:ss"
    if kind == "date":
        win32_format = win32_datetime_format(LOCALE_SSHORTDATE)
    elif kind == "time":
        win32_format = win32_datetime_format(LOCALE_STIMEFORMAT)
    else:  # kind == "datetime":
        win32_format = (
            win32_datetime_format(LOCALE_SSHORTDATE)
            + " "
            + win32_datetime_format(LOCALE_STIMEFORMAT)
        )
    return msoffice_datetime_format_from_win32(win32_format)


def win32_datetime_format(lctype_constant: int) -> str:
    """
    Get the Windows .NET locale format string for the given `lctype`, where `lctype` is one of the LOCALE_*
    constants, e.g., LOCALE_SSHORTDATE or LOCALE_STIMEFORMAT.

    See: https://github.com/tpn/winsdk-10/blob/master/Include/10.0.10240.0/um/WinNls.h

    :param lctype: The local constant to retrieve, e.g. LOCALE_SSHORTDATE (0x0000001F).
    :return str: The windows locale format string, e.g. "dd/MM/yyyy".
    """

    LOCALE_USER_DEFAULT = 0x0400  # Code for the user's default locale, e.g., "en-US"
    buffer = ctypes.create_unicode_buffer(100)
    ctypes.windll.kernel32.GetLocaleInfoW(LOCALE_USER_DEFAULT, lctype_constant, buffer, len(buffer))
    return str(buffer.value)


#################################################################################
# Miscellaneous datetime helpers
#################################################################################


def periodic_integer(
    *,
    seed: datetime.datetime | datetime.timedelta | int | None = None,
    interval: int = 1,
    minimum: int,
    maximum: int,
) -> int:
    """
    Deterministically generate an integer in a closed range.

    For a given `seed`, returns an integer in [`minimum`, `maximum`], repeating every `interval` * (`maximum` -
    `minimum` + 1). Output advances by 1 every `interval` steps, cycling through the entire range.

    - If `seed` is None, the current time is used.
    - If `seed` is a `datetime`, it is converted to seconds since the epoch.
    - If `seed` is a `timedelta`, its total seconds is used.
    - If `seed` is an `int`, it is interpreted directly.

    :param minimum: Minimum integer value (inclusive).
    :param maximum: Maximum integer value (inclusive).
    :param interval: Interval length for each step in the sequence, default is 1 (i.e. unused).
    :param seed: Reference value for mapping (`datetime`, `timedelta`, or `int`), default is the current time.
    :return int: An integer in [`minimum`, `maximum`], cycling through the range as `seed` increases.
    :raises TypeError: If `seed` is not one of `datetime`, `timedelta`, or `int`.
    """
    if isinstance(seed, datetime.datetime):
        _seed: int = int((seed - datetime.datetime.min).total_seconds())
    elif isinstance(seed, datetime.timedelta):
        _seed: int = int(seed.total_seconds())
    elif isinstance(seed, int):
        _seed: int = seed
    elif seed is None:
        _seed: int = int((now_utc() - datetime.datetime.min).total_seconds())
    else:
        raise TypeError(f"Unsupported seed type: {type(seed)}. Must be datetime, timedelta, or int.")
    _range_size: int = maximum - minimum + 1
    _result: int = (_seed // interval) % _range_size + minimum
    return _result


def is_datetime_in_range(
    datetime: datetime.datetime,
    since_date: datetime.date,
    until_date: datetime.date,
    tz: datetime.timezone,
) -> bool:
    """
    Check if a datetime falls within a date range (inclusive lower, exclusive upper), using the given timezone.
    :param datetime: The datetime to check.
    :param since_date: The start of the range (inclusive).
    :param until_date: The end of the range (exclusive).
    :param tz: The timezone to use for comparison.
    :returns bool: True if the datetime falls within the range; False otherwise.
    """
    assert datetime.tzinfo is not None, "datetime must have timezone info"
    _date = datetime.astimezone(tz).date()
    if _date < since_date:
        return False
    return not _date >= until_date


# End of file: python/plib_/base/datetime_helpers.py
