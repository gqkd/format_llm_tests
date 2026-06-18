"""
Score generated Python code with pass@1 subprocess execution.

Input: Candidate code, pytest-style tests, working directory, and timeout.

Processing: Writes code/tests to an isolated temp directory and runs pytest in a subprocess.

Output: Execution result with pass/fail, captured output, timeout, and error metadata.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class CodeExecResult(BaseModel):
    """pass@1 execution result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    passed: bool
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    error: str | None
    work_dir: str


def score_python_code_pass_at_1(
    *,
    code: str,
    tests: str,
    work_dir: str | Path | None = None,
    timeout_seconds: float = 10.0,
) -> CodeExecResult:
    """Run candidate Python code against tests in an isolated subprocess."""

    path, cleanup = _prepare_work_dir(work_dir)
    try:
        (path / "solution.py").write_text(code, encoding="utf-8")
        (path / "test_solution.py").write_text(tests, encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", str(path / "test_solution.py")],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return CodeExecResult(
            passed=completed.returncode == 0,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            timed_out=False,
            error=None,
            work_dir=str(path),
        )
    except subprocess.TimeoutExpired as exc:
        return CodeExecResult(
            passed=False,
            exit_code=None,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            timed_out=True,
            error=f"timeout after {timeout_seconds} seconds",
            work_dir=str(path),
        )
    finally:
        if cleanup:
            shutil.rmtree(path, ignore_errors=True)


def _prepare_work_dir(work_dir: str | Path | None) -> tuple[Path, bool]:
    if work_dir is not None:
        path = Path(work_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path, False
    return Path(tempfile.mkdtemp(prefix="format-llm-code-")), True
