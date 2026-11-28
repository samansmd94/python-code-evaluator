"""Optional tests that exercise submissions in real disposable containers."""

import os
import subprocess

import pytest

from backend.app.execution.docker_runner import DockerRunner
from backend.app.execution.protocol import CaseInput

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_DOCKER_INTEGRATION") != "1",
    reason="Set RUN_DOCKER_INTEGRATION=1 to run real Docker integration tests",
)


class TrackingDockerRunner(DockerRunner):
    """Capture the unique name so each real test can verify container removal."""

    last_container_name: str | None = None

    def _container_command(self, container_name: str) -> list[str]:
        self.last_container_name = container_name
        return super()._container_command(container_name)


def _assert_container_removed(runner: TrackingDockerRunner) -> None:
    assert runner.last_container_name is not None
    result = subprocess.run(
        ["docker", "container", "inspect", runner.last_container_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
        check=False,
    )
    assert result.returncode != 0


def test_valid_result_survives_json_dumps_monkeypatch():
    runner = TrackingDockerRunner()
    results = runner.execute(
        "import json\n"
        "json.dumps = lambda *args, **kwargs: '{\"actual\":999}'\n"
        "def add(a, b):\n    return 0\n",
        "add",
        [CaseInput(case_number=1, input_data=[2, 3])],
    )
    assert len(results) == 1
    assert results[0].status == "returned"
    assert results[0].actual == 0
    _assert_container_removed(runner)


def test_source_syntax_error_and_runtime_syntax_error_are_distinct():
    compile_error_runner = TrackingDockerRunner()
    compile_error = compile_error_runner.execute(
        "def add(:\n", "add", [CaseInput(case_number=1, input_data=[2, 3])]
    )
    assert compile_error[0].status == "syntax_error"
    _assert_container_removed(compile_error_runner)

    runtime_error_runner = TrackingDockerRunner()
    runtime_error = runtime_error_runner.execute(
        "def add(a, b):\n    raise SyntaxError('raised at runtime')\n",
        "add",
        [CaseInput(case_number=1, input_data=[2, 3])],
    )
    assert runtime_error[0].status == "runtime_error"
    _assert_container_removed(runtime_error_runner)


def test_container_is_removed_after_controlled_execution_failure():
    runner = TrackingDockerRunner()
    result = runner.execute(
        "def add(a, b):\n    raise RuntimeError('expected test failure')\n",
        "add",
        [CaseInput(case_number=1, input_data=[2, 3])],
    )
    assert result[0].status == "runtime_error"
    _assert_container_removed(runner)


def test_missing_function_malformed_output_and_oversized_result_are_bounded():
    missing_runner = TrackingDockerRunner()
    missing = missing_runner.execute(
        "def other(a, b):\n    return a + b\n",
        "add",
        [CaseInput(case_number=1, input_data=[2, 3])],
    )
    assert missing[0].status == "missing_function"
    _assert_container_removed(missing_runner)

    malformed_runner = TrackingDockerRunner()
    malformed = malformed_runner.execute(
        "import os\n"
        "def add(a, b):\n"
        "    os.write(1, b'not-json')\n"
        "    return a + b\n",
        "add",
        [CaseInput(case_number=1, input_data=[2, 3])],
    )
    assert malformed[0].status == "runtime_error"
    _assert_container_removed(malformed_runner)

    oversized_runner = TrackingDockerRunner()
    oversized = oversized_runner.execute(
        "def add(a, b):\n    return 'x' * 9000\n",
        "add",
        [CaseInput(case_number=1, input_data=[2, 3])],
    )
    assert oversized[0].status == "output_limit"
    _assert_container_removed(oversized_runner)


def test_container_is_removed_after_case_timeout():
    runner = TrackingDockerRunner()
    result = runner.execute(
        "def add(a, b):\n    while True:\n        pass\n",
        "add",
        [CaseInput(case_number=1, input_data=[2, 3])],
    )
    assert result[0].status == "timeout"
    _assert_container_removed(runner)
