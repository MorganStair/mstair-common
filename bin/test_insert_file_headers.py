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
    • Globbing expansion for wildcard arguments
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr
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


# --------------------------------------------------------------
# Utility context manager
# --------------------------------------------------------------
@contextmanager
def chdir(path: Path):
    """Temporarily change working directory."""
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


# --------------------------------------------------------------
# Main test suite
# --------------------------------------------------------------
class TestInsertFileHeaders(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="hdrtest_"))

    def _write(self, name: str, text: str) -> Path:
        path = self.tmpdir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def _read(self, path: Path) -> list[str]:
        return path.read_text(encoding="utf-8").splitlines()

    # ----------------------------------------------------------
    # Core functional tests
    # ----------------------------------------------------------
    def test_python_file_with_shebang(self) -> None:
        with chdir(self.tmpdir):
            path = self._write("script.py", "#!/usr/bin/env python3\nprint('hi')\n")
            with redirect_stderr(io.StringIO()):
                ok = ifh.process_file(path)
            self.assertTrue(ok)
            lines = self._read(path)
            self.assertTrue(lines[0].startswith("#!"))
            self.assertRegex(lines[1], r"^# File: script\.py$")
            self.assertEqual(lines[-2], "")
            self.assertEqual(lines[-1], ifh.FOOTER_LINE)

    def test_makefile_fragment(self) -> None:
        with chdir(self.tmpdir):
            path = self._write("build.mk", "VAR=value\n")
            ifh.process_file(path)
            lines = self._read(path)
            self.assertEqual(lines[0], "# File: build.mk")
            self.assertEqual(lines[-2], "")
            self.assertEqual(lines[-1], ifh.FOOTER_LINE)

    def test_existing_header_footer_replaced(self) -> None:
        with chdir(self.tmpdir):
            path = self._write(
                "file.mak",
                f"# File: old.mak\nVALUE=1\n\n{ifh.FOOTER_LINE}\n",
            )
            ifh.process_file(path)
            lines = self._read(path)
            self.assertEqual(lines[0], "# File: file.mak")
            self.assertEqual(lines[-2], "")
            self.assertEqual(lines[-1], ifh.FOOTER_LINE)
            self.assertNotIn("old.mak", "".join(lines))

    def test_trailing_blank_lines_collapsed(self) -> None:
        with chdir(self.tmpdir):
            path = self._write("manyblanks.mk", "X=1\n\n\n\n")
            ifh.process_file(path)
            lines = self._read(path)
            self.assertEqual(lines[-2], "")
            self.assertEqual(lines[-1], ifh.FOOTER_LINE)

    def test_idempotent_second_run(self) -> None:
        with chdir(self.tmpdir):
            path = self._write("repeat.py", "print('x')\n")
            ifh.process_file(path)
            first = self._read(path)
            ifh.process_file(path)
            second = self._read(path)
            self.assertEqual(first, second)

    def test_skip_unsupported_extension(self) -> None:
        with chdir(self.tmpdir):
            path = self._write("notes.txt", "hello\n")
            stderr_buf = io.StringIO()
            with redirect_stderr(stderr_buf):
                ok = ifh.process_file(path)
            self.assertFalse(ok)
            self.assertIn("unsupported extension", stderr_buf.getvalue())

    # ----------------------------------------------------------
    # Globbing and CLI tests
    # ----------------------------------------------------------
    def test_expand_args_with_globs(self) -> None:
        with chdir(self.tmpdir):
            f1 = self._write("src/a.py", "print('A')\n")
            f2 = self._write("src/b.py", "print('B')\n")
            f3 = self._write("docs/readme.txt", "not allowed\n")

            results = ifh.expand_args(["src/*.py", "docs/*.txt"])
            self.assertIn(f1.resolve(), results)
            self.assertIn(f2.resolve(), results)
            # expand_args filters unsupported extensions
            self.assertNotIn(f3.resolve(), results)

    def test_main_with_glob_patterns(self) -> None:
        with chdir(self.tmpdir):
            f1 = self._write("src/one.py", "print('one')\n")
            f2 = self._write("src/two.mk", "VAR=1\n")

            argv = ["src/*.py", "src/*.mk"]
            with redirect_stderr(io.StringIO()):
                code = ifh.insert_file_headers_main(argv)

            self.assertEqual(code, 0)
            for f in (f1, f2):
                lines = self._read(f)
                self.assertIn(ifh.FOOTER_LINE, lines)
                # Expect relative header, not absolute
                self.assertEqual(lines[0], f"# File: {f.relative_to(self.tmpdir).as_posix()}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
