#!/usr/bin/env python3
"""
Unit tests for insert_file_headers.py.

Validates:
    • Allowed extensions (.py, .mk, .mak)
    • Proper header/footer insertion and replacement
    • Preservation of shebang line
    • Exactly one blank line before the footer
    • Idempotent output (second run makes no changes)
    • Skip behavior for unsupported file types
"""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path


# --------------------------------------------------------------
# Ensure the bin/ directory is on sys.path so we can import the script.
# --------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
BIN_DIR = ROOT_DIR / "bin"
if str(BIN_DIR) not in sys.path:
    sys.path.insert(0, str(BIN_DIR))

try:
    import insert_file_headers as ifh  # type: ignore
except ImportError as exc:
    raise SystemExit(f"Cannot import insert_file_headers from {BIN_DIR}: {exc}") from exc


class TestInsertFileHeaders(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="hdrtest_"))

    def _write(self, name: str, text: str) -> Path:
        path = self.tmpdir / name
        path.write_text(text, encoding="utf-8")
        return path

    def _read(self, path: Path) -> list[str]:
        return path.read_text(encoding="utf-8").splitlines()

    # ----------------------------------------------------------
    # Core functional tests
    # ----------------------------------------------------------
    def test_python_file_with_shebang(self) -> None:
        path = self._write("script.py", "#!/usr/bin/env python3\nprint('hi')\n")
        with redirect_stderr(io.StringIO()):
            ok = ifh.process_file(path)
        self.assertTrue(ok)
        lines = self._read(path)
        self.assertTrue(lines[0].startswith("#!"))
        self.assertRegex(lines[1], r"^# File: .+/script\.py$")
        self.assertEqual(lines[-2], "")
        self.assertEqual(lines[-1], ifh.FOOTER_LINE)

    def test_makefile_fragment(self) -> None:
        path = self._write("build.mk", "VAR=value\n")
        ifh.process_file(path)
        lines = self._read(path)
        self.assertEqual(lines[0], f"# File: {path.as_posix()}")
        self.assertEqual(lines[-2], "")
        self.assertEqual(lines[-1], ifh.FOOTER_LINE)

    def test_existing_header_footer_replaced(self) -> None:
        path = self._write(
            "file.mak",
            f"# File: old.mak\nVALUE=1\n\n{ifh.FOOTER_LINE}\n",
        )
        ifh.process_file(path)
        lines = self._read(path)
        self.assertIn(f"# File: {path.as_posix()}", lines[0])
        self.assertEqual(lines[-2], "")
        self.assertEqual(lines[-1], ifh.FOOTER_LINE)
        self.assertNotIn("old.mak", "".join(lines))

    def test_trailing_blank_lines_collapsed(self) -> None:
        content = "X=1\n\n\n\n"
        path = self._write("manyblanks.mk", content)
        ifh.process_file(path)
        lines = self._read(path)
        self.assertEqual(lines[-2], "")
        self.assertEqual(lines[-1], ifh.FOOTER_LINE)

    def test_idempotent_second_run(self) -> None:
        path = self._write("repeat.py", "print('x')\n")
        ifh.process_file(path)
        first = self._read(path)
        ifh.process_file(path)
        second = self._read(path)
        self.assertEqual(first, second)

    def test_skip_unsupported_extension(self) -> None:
        path = self._write("notes.txt", "hello\n")
        stderr_buf = io.StringIO()
        with redirect_stderr(stderr_buf):
            ok = ifh.process_file(path)
        self.assertFalse(ok)
        self.assertIn("unsupported extension", stderr_buf.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
