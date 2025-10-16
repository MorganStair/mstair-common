# File: src/mstair/common/io/display_formatter.py
"""
Console display formatting utilities (ASCII-only).

This module provides a lightweight, dependency-free set of helpers for
rendering lists of dictionaries as readable text for console or log output.
All output is strictly ASCII-only—no color, Unicode box drawing, or control
characters—so results are safe for plain-text logs and CI terminals.

The `DisplayFormatter` class supports three main formats:
- CSV text via `to_csv()`
- JSON text via `to_json()`
- Fixed-width ASCII tables via `to_table()`

It also provides higher-level summary views for traced email data and other
structured records, ensuring consistent visual layout.

Example:
    >>> from datetime import datetime
    >>> from mstair.common.io.display_formatter import DisplayFormatter
    >>> rows = [
    ...     {"date": datetime(2025, 10, 10, 9, 30), "from": "info@example.com", "subject": "Welcome"},
    ...     {"date": datetime(2025, 10, 11, 14, 45), "from": "support@example.com", "subject": "Follow-up"},
    ... ]
    >>> fmt = DisplayFormatter()
    >>> print(fmt.to_table(rows))
    date                 | from                 | subject
    ---------------------+----------------------+-----------
    2025-10-10 09:30     | info@example.com     | Welcome
    2025-10-11 14:45     | support@example.com  | Follow-up
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable
from datetime import datetime
from typing import Any


class DisplayFormatter:
    def to_csv(self, rows: list[dict[str, Any]], columns: list[str] | None = None) -> str:
        """
        Serialize a list of dictionaries to CSV format (ASCII-only).

        Args:
            rows: List of dictionaries representing data rows.
            columns: Optional list of column names to include and order. If None, uses keys from the first row.

        Returns:
            CSV-formatted string with header and rows, using only ASCII characters.
        """

        if not rows:
            return ""
        output = io.StringIO()
        cols = columns or list(rows[0].keys())
        writer = csv.DictWriter(output, fieldnames=cols, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            # Ensure all columns present
            out_row = {col: row.get(col, "") for col in cols}
            writer.writerow(out_row)
        return output.getvalue()

    def to_json(self, rows: list[dict[str, Any]]) -> str:
        """
        Serialize a list of dictionaries to pretty-printed JSON (ASCII-only).

        Args:
            rows: List of dictionaries representing data rows.

        Returns:
            JSON-formatted string, pretty-printed, with ensure_ascii=True.
        """

        return json.dumps(rows, ensure_ascii=True, indent=2)

    def to_table(self, rows: list[dict[str, Any]], columns: list[str] | None = None) -> str:
        """
        Render a list of dictionaries as an ASCII table (pipes and dashes only).

        Args:
            rows: List of dictionaries representing data rows.
            columns: Optional list of column names to include and order. If None, uses keys from the first row.

        Returns:
            Multi-line ASCII string representing the table, suitable for console output.
        """
        if not rows:
            return "(no data)"
        cols = columns or list(rows[0].keys())
        # Compute column widths
        col_widths = {
            col: max(len(str(col)), max((len(str(r.get(col, ""))) for r in rows), default=0))
            for col in cols
        }
        # Header
        header = " | ".join(col.ljust(col_widths[col]) for col in cols)
        sep = "-+-".join("-" * col_widths[col] for col in cols)
        lines = [header, sep]
        for row in rows:
            line = " | ".join(str(row.get(col, "")).ljust(col_widths[col]) for col in cols)
            lines.append(line)
        return "\n".join(lines)

    """Format collections for console display in ASCII-only text."""

    def format_trace_results(self, confirmation: str, emails: Iterable[dict[str, Any]]) -> str:
        """
        Format email trace results for display in a human-readable ASCII summary.

        Args:
            confirmation: The confirmation token searched.
            emails: Iterable of dictionaries with keys: id, date, from, subject, snippet.

        Returns:
            Multi-line ASCII string intended for console printing.
        """
        items: list[dict[str, Any]] = list(emails)
        lines: list[str] = []
        lines.append(f"Confirmation {confirmation} - Email Trace Results")
        lines.append("=" * 72)
        if not items:
            lines.append("No related emails found")
            return "\n".join(lines)

        # Compute range
        dates: list[datetime] = []
        for e in items:
            dt = e.get("date")
            if isinstance(dt, datetime):
                dates.append(dt)
        if dates:
            start = min(dates)
            end = max(dates)
            lines.append(f"Found {len(items)} related emails ({start:%Y-%m-%d} - {end:%Y-%m-%d})")
        else:
            lines.append(f"Found {len(items)} related emails")
        lines.append("")

        # Table-like view
        lines.append("Date                 From                          Subject")
        lines.append("-" * 72)
        for e in items:
            date = e.get("date")
            datestr = date.strftime("%Y-%m-%d %H:%M") if isinstance(date, datetime) else "".ljust(16)
            sender = str(e.get("from", ""))[:28].ljust(28)
            subject = str(e.get("subject", ""))
            lines.append(f"{datestr}  {sender}  {subject}")

        return "\n".join(lines)

    def format_generic_results(self, title: str, items: Iterable[dict[str, Any]]) -> str:
        """
        Format a generic list of email-like dicts for console display in ASCII.

        Args:
            title: Header title line.
            items: Iterable of dicts with keys: date, from, subject.

        Returns:
            Multi-line ASCII string for console output.
        """
        rows: list[dict[str, Any]] = list(items)
        lines: list[str] = []
        lines.append(title)
        lines.append("=" * 72)
        if not rows:
            lines.append("No results found")
            return "\n".join(lines)

        dates: list[datetime] = []
        for e in rows:
            dt = e.get("date")
            if isinstance(dt, datetime):
                dates.append(dt)
        if dates:
            start = min(dates)
            end = max(dates)
            lines.append(f"Found {len(rows)} results ({start:%Y-%m-%d} - {end:%Y-%m-%d})")
        else:
            lines.append(f"Found {len(rows)} results")
        lines.append("")

        lines.append("Date                 From                          Subject")
        lines.append("-" * 72)
        for e in rows:
            date = e.get("date")
            datestr = date.strftime("%Y-%m-%d %H:%M") if isinstance(date, datetime) else "".ljust(16)
            sender = str(e.get("from", ""))[:28].ljust(28)
            subject = str(e.get("subject", ""))
            lines.append(f"{datestr}  {sender}  {subject}")

        return "\n".join(lines)


# End of file: src/mstair/common/io/display_formatter.py
