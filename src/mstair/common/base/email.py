"""
mstair.common.base.email - Email related helpers
"""

from __future__ import annotations

import re
from email.utils import parseaddr
from typing import NamedTuple


# --- simple, fast ASCII validators -------------------------------------------------

_ADDR_LOCAL_RE: re.Pattern[str] = re.compile(r"^[a-z0-9!#$%&'*+/=?^_`{|}~.-]+$", flags=re.IGNORECASE)
_DOMAIN_LABEL_RE: re.Pattern[str] = re.compile(
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)", flags=re.IGNORECASE
)
_ADDR_DOMAIN_RE: re.Pattern[str] = re.compile(
    rf"^(?:{_DOMAIN_LABEL_RE.pattern}\.)+[a-z]{{2,63}}$", flags=re.IGNORECASE
)


class NameAddr(NamedTuple):
    name: str
    addr: str

    def __bool__(self) -> bool:
        return bool(self.addr)


def name_addr_from_email(
    email: str,
    *,
    strict: bool = False,
    max_name_len: int = 32,
    max_addr_len: int = 96,
) -> NameAddr:
    """
    Parse "Name <user@example.com>" (strict=True) or tolerate bare addr (default).

    :param str email: Source string like "User Name <user@example.com>".
    :param bool strict: If True, require angle-bracket form; reject multiples/oddities.
    :param int max_name_len: Maximum name length.
    :param int max_addr_len: Maximum full address length.
    :return: NameAddr(name, email) or NameAddr('', '') if invalid.
    """
    display_name: str
    addr: str
    display_name, addr = parseaddr(email, strict=strict)
    if not addr:
        return NameAddr(name="", addr="")

    local_part: str
    sep: str
    domain: str
    local_part, sep, domain = addr.rpartition("@")
    if (
        sep != "@"
        or not local_part
        or not domain
        or not local_part.isascii()
        or not _ADDR_LOCAL_RE.search(local_part)
        or local_part.startswith(".")
        or local_part.endswith(".")
        or ".." in local_part
        or local_part.startswith('"')
        or local_part.endswith('"')
        or len(local_part) > max_name_len
        or not domain.isascii()
        or not _ADDR_DOMAIN_RE.search(domain)
        or len(local_part) + len(domain) + 1 > max_addr_len
        or len(domain) > 255
    ):
        return NameAddr(name="", addr="")

    return NameAddr(
        name=display_name.strip(),
        addr="{local}@{domain}".format(
            local=local_part,
            domain=domain.lower(),
        ),
    )
