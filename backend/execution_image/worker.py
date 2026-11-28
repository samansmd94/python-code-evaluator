"""Container supervisor with a separate per-case process for submitted code."""

import contextlib
import io
import json
import os
import resource
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MAX_INPUT_BYTES = 1024 * 1024
MAX_SOURCE_BYTES = 32 * 1024
MAX_CASES = 50
MAX_CASE_INPUT_BYTES = 64 * 1024
MAX_CASE_STDIO_BYTES = 8 * 1024
MAX_CASE_RESULT_BYTES = 8 * 1024
CASE_TIMEOUT_SECONDS = 2.0
CASE_EXIT_SYNTAX_ERROR = 20
CASE_EXIT_RUNTIME_ERROR = 21
CASE_EXIT_OUTPUT_LIMIT = 22
CASE_EXIT_MISSING_FUNCTION = 23
CASE_EXIT_RESULT_INVALID = 24
SAFE_ENVIRONMENT = {
    "HOME": "/tmp",
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONUNBUFFERED": "1",
}
_trusted_json_dumps = json.dumps


class OutputLimitReached(Exception):
    """Raised when submitted code writes beyond its stream limit."""


class BoundedTextWriter(io.TextIOBase):
    """Discard captured text after a fixed UTF-8 byte budget."""

    def __init__(self, limit):
        self.limit = limit
        self.byte_count = 0

    def write(self, value):
        size = len(value.encode("utf-8", errors="replace"))
        if self.byte_count + size > self.limit:
            raise OutputLimitReached
        self.byte_count += size
        return len(value)

    def flush(self):
        return None


def _set_child_limits():
    resource.setrlimit(resource.RLIMIT_CPU, (2, 3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_CASE_STDIO_BYTES, MAX_CASE_STDIO_BYTES))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))


def _kill_process_group(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except OSError:
        process.kill()


def _reject_json_constant(value):
    raise ValueError("Non-standard JSON constant")


def _call_submission(source, function_name, input_data):
    """Run one test in a fresh Python process and bound all captured output."""
    payload = json.dumps(input_data, ensure_ascii=False, allow_nan=False).encode("utf-8")
    with tempfile.TemporaryDirectory(dir="/tmp") as case_dir:
        source_path = Path(case_dir) / "submission.py"
        source_path.write_text(source, encoding="utf-8")
        source_path.chmod(0o444)
        stdout_path = Path(case_dir) / "stdout"
        stderr_path = Path(case_dir) / "stderr"
        started = time.monotonic()
        with stdout_path.open("w+b") as stdout_file, stderr_path.open("w+b") as stderr_file:
            process = subprocess.Popen(
                [sys.executable, "-I", __file__, "call", source_path, function_name],
                stdin=subprocess.PIPE,
                stdout=stdout_file,
                stderr=stderr_file,
                cwd=case_dir,
                env=SAFE_ENVIRONMENT,
                start_new_session=True,
                preexec_fn=_set_child_limits,
            )
            try:
                process.communicate(payload, timeout=CASE_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                _kill_process_group(process)
                process.wait()
                return {
                    "status": "timeout",
                    "actual": None,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                }
            finally:
                _kill_process_group(process)

            duration_ms = int((time.monotonic() - started) * 1000)
            stdout_file.flush()
            stderr_file.flush()
            if stdout_file.tell() >= MAX_CASE_STDIO_BYTES or stderr_file.tell() >= MAX_CASE_STDIO_BYTES:
                return {"status": "output_limit", "actual": None, "duration_ms": duration_ms}

            exit_statuses = {
                CASE_EXIT_SYNTAX_ERROR: "syntax_error",
                CASE_EXIT_RUNTIME_ERROR: "runtime_error",
                CASE_EXIT_OUTPUT_LIMIT: "output_limit",
                CASE_EXIT_MISSING_FUNCTION: "missing_function",
                CASE_EXIT_RESULT_INVALID: "runtime_error",
            }
            if process.returncode in exit_statuses:
                return {
                    "status": exit_statuses[process.returncode],
                    "actual": None,
                    "duration_ms": duration_ms,
                }
            if process.returncode != 0:
                return {"status": "runtime_error", "actual": None, "duration_ms": duration_ms}

            stdout_file.seek(0)
            output = stdout_file.read(MAX_CASE_RESULT_BYTES + 1)
            if len(output) > MAX_CASE_RESULT_BYTES:
                return {"status": "runtime_error", "actual": None, "duration_ms": duration_ms}
            try:
                actual = json.loads(output, parse_constant=_reject_json_constant)
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                return {"status": "runtime_error", "actual": None, "duration_ms": duration_ms}
            return {"status": "returned", "actual": actual, "duration_ms": duration_ms}


def _call_mode(source_path, function_name):
    """Execute one case in a child; the container supervisor classifies its exit."""
    try:
        case_input = json.loads(sys.stdin.buffer.read(MAX_CASE_INPUT_BYTES + 1))
        if not isinstance(case_input, list):
            raise ValueError
        source = Path(source_path).read_text(encoding="utf-8")
        if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
            raise ValueError
    except Exception:
        raise SystemExit(CASE_EXIT_RUNTIME_ERROR)

    try:
        code = compile(source, "<submission>", "exec")
    except SyntaxError:
        raise SystemExit(CASE_EXIT_SYNTAX_ERROR)

    # Keep trusted references local before submitted code runs. Result status and
    # the outer worker response are built by the separate supervisor process.
    serialize_result = json.dumps
    captured_stdout = BoundedTextWriter(MAX_CASE_STDIO_BYTES)
    captured_stderr = BoundedTextWriter(MAX_CASE_STDIO_BYTES)
    case_exit_status = None
    try:
        with contextlib.redirect_stdout(captured_stdout), contextlib.redirect_stderr(captured_stderr):
            namespace = {"__name__": "_submitted_solution"}
            try:
                exec(code, namespace)
            except OutputLimitReached:
                case_exit_status = CASE_EXIT_OUTPUT_LIMIT
            except BaseException:
                case_exit_status = CASE_EXIT_RUNTIME_ERROR

            if case_exit_status is None:
                function = namespace.get(function_name)
                if not callable(function):
                    case_exit_status = CASE_EXIT_MISSING_FUNCTION
                    actual = None
                else:
                    try:
                        actual = function(*case_input)
                    except OutputLimitReached:
                        case_exit_status = CASE_EXIT_OUTPUT_LIMIT
                    except BaseException:
                        case_exit_status = CASE_EXIT_RUNTIME_ERROR

    except BaseException:
        raise SystemExit(CASE_EXIT_RUNTIME_ERROR)

    if case_exit_status is not None:
        raise SystemExit(case_exit_status)

    try:
        serialized = serialize_result(actual, ensure_ascii=False, allow_nan=False)
        output = serialized.encode("utf-8")
    except Exception:
        raise SystemExit(CASE_EXIT_RESULT_INVALID)
    if len(output) > MAX_CASE_RESULT_BYTES:
        raise SystemExit(CASE_EXIT_OUTPUT_LIMIT)
    sys.stdout.buffer.write(output)


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "call":
        _call_mode(sys.argv[2], sys.argv[3])
        return

    raw_payload = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw_payload) > MAX_INPUT_BYTES:
        raise SystemExit(2)
    payload = json.loads(raw_payload)
    source = payload.get("source_code")
    function_name = payload.get("function_name")
    cases = payload.get("test_cases")
    if (
        not isinstance(source, str)
        or len(source.encode("utf-8")) > MAX_SOURCE_BYTES
        or not isinstance(function_name, str)
        or not function_name.isidentifier()
        or not isinstance(cases, list)
        or not cases
        or len(cases) > MAX_CASES
    ):
        raise SystemExit(2)

    results = []
    for case in cases:
        case_number = case.get("case_number")
        case_input = case.get("input_data")
        if not isinstance(case_number, int) or case_number < 1 or not isinstance(case_input, list):
            raise SystemExit(2)
        outcome = _call_submission(source, function_name, case_input)
        outcome["case_number"] = case_number
        results.append(outcome)

    sys.stdout.write(_trusted_json_dumps({"results": results}, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
