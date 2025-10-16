import datetime

from mstair.common.io.display_formatter import DisplayFormatter


def test_to_csv_ascii_and_columns() -> None:
    fmt = DisplayFormatter()
    rows = [
        {"a": 1, "b": 2},
        {"a": 3, "b": 4},
    ]
    out = fmt.to_csv(rows)
    assert "a,b" in out
    assert "1,2" in out and "3,4" in out
    _ascii_only(out)
    # Custom columns
    out2 = fmt.to_csv(rows, columns=["b", "a"])
    assert out2.startswith("b,a")
    _ascii_only(out2)


def test_to_json_ascii() -> None:
    fmt = DisplayFormatter()
    rows = [
        {"a": 1, "b": 2},
        {"a": 3, "b": 4},
    ]
    out = fmt.to_json(rows)
    assert out.strip().startswith("[")
    assert '"a": 1' in out
    _ascii_only(out)


def test_to_table_ascii_and_columns() -> None:
    fmt = DisplayFormatter()
    rows = [
        {"a": "foo", "b": "bar"},
        {"a": "baz", "b": "qux"},
    ]
    out = fmt.to_table(rows)
    assert "a" in out and "b" in out
    assert "foo" in out and "baz" in out
    _ascii_only(out)
    # Custom columns
    out2 = fmt.to_table(rows, columns=["b", "a"])
    header = out2.splitlines()[0].strip()
    # Accept any amount of padding between columns
    assert header.replace(" ", "").startswith("b|a")
    _ascii_only(out2)


def test_to_table_empty() -> None:
    fmt = DisplayFormatter()
    out = fmt.to_table([])
    assert "no data" in out
    _ascii_only(out)


def _ascii_only(s: str) -> None:
    s.encode("ascii")


def test_format_trace_results_empty() -> None:
    fmt = DisplayFormatter()
    out = fmt.format_trace_results("616882420288", [])
    assert "Confirmation 616882420288 - Email Trace Results" in out
    assert "No related emails found" in out
    _ascii_only(out)


def test_format_trace_results_single() -> None:
    fmt = DisplayFormatter()
    data = [
        {
            "id": "m1",
            "date": datetime.datetime(2024, 12, 2, 9, 30),
            "from": "Sender",
            "subject": "Subj",
            "snippet": "",
        }
    ]
    out = fmt.format_trace_results("616882420288", data)
    assert "Found 1 related emails" in out
    assert "Sender" in out and "Subj" in out
    _ascii_only(out)


def test_format_trace_results_multiple_date_range() -> None:
    fmt = DisplayFormatter()
    data = [
        {
            "id": "m1",
            "date": datetime.datetime(2024, 12, 1, 10, 0),
            "from": "A",
            "subject": "S1",
            "snippet": "",
        },
        {
            "id": "m2",
            "date": datetime.datetime(2024, 12, 2, 9, 30),
            "from": "B",
            "subject": "S2",
            "snippet": "",
        },
    ]
    out = fmt.format_trace_results("616882420288", data)
    assert "Found 2 related emails (2024-12-01 - 2024-12-02)" in out
    _ascii_only(out)
