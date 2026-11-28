"""Unit tests for fixed Docker configuration, parsing, and cleanup."""

import json
import subprocess
import sys

import pytest

from backend.app.execution import docker_runner as runner_module
from backend.app.execution.docker_runner import (
    ContainerCleanupError,
    ContainerOutputLimitError,
    ContainerTimedOutError,
    DockerRunner,
    DockerUnavailableError,
    RunnerImageUnavailableError,
)
from backend.app.execution.limits import EXECUTION_IMAGE
from backend.app.execution.protocol import CaseInput


def _cases():
    return [CaseInput(case_number=1, input_data=[2, 3])]


def test_container_command_uses_fixed_restrictive_options():
    command = DockerRunner()._container_command("pce-run-abc123")
    assert command[0:2] == ["docker", "run"]
    assert "--pull=never" in command
    assert command[command.index("--network") + 1] == "none"
    assert command[command.index("--user") + 1] == "10001:10001"
    assert "--read-only" in command
    assert "--cap-drop" in command
    assert command[command.index("--cap-drop") + 1] == "ALL"
    assert command[command.index("--pids-limit") + 1] == "32"
    assert command[command.index("--memory") + 1] == "128m"
    assert command[-1] == EXECUTION_IMAGE
    assert "--rm" in command
    assert not any(arg in {"--mount", "-v", "--volume", "--privileged", "--env"} for arg in command)


def test_docker_preflight_distinguishes_daemon_and_image_failures(monkeypatch):
    runner = DockerRunner()

    def missing_docker(*_args, **_kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(runner_module.subprocess, "run", missing_docker)
    with pytest.raises(DockerUnavailableError):
        runner._check_docker()

    calls = []

    def no_image(command, **_kwargs):
        calls.append(command)
        code = 1 if "image" in command else 0
        return subprocess.CompletedProcess(command, code, stdout=b"", stderr=b"hidden")

    monkeypatch.setattr(runner_module.subprocess, "run", no_image)
    with pytest.raises(RunnerImageUnavailableError):
        runner._check_docker()
    assert calls[0][0:2] == ["docker", "version"]
    assert calls[1][0:3] == ["docker", "image", "inspect"]


def test_runner_parses_worker_results_and_cleans_up(monkeypatch):
    runner = DockerRunner()
    removed = []
    command_seen = []

    monkeypatch.setattr(runner, "_check_docker", lambda: None)
    monkeypatch.setattr(
        runner,
        "_run_bounded",
        lambda command, payload, _timeout: (
            command_seen.append((command, json.loads(payload)))
            or (0, b'{"results":[{"case_number":1,"status":"returned","actual":5,"duration_ms":2}]}', b"")
        ),
    )
    monkeypatch.setattr(runner, "_remove_container", removed.append)

    results = runner.execute("def add(a, b): return a + b", "add", _cases())
    assert results[0].actual == 5
    command, payload = command_seen[0]
    assert payload["function_name"] == "add"
    assert payload["test_cases"] == [{"case_number": 1, "input_data": [2, 3]}]
    assert "--network" in command
    assert len(removed) == 1
    assert removed[0].startswith("pce-run-")


@pytest.mark.parametrize(
    "failure,expected",
    [
        (ContainerTimedOutError(), ContainerTimedOutError),
        (ContainerOutputLimitError(), ContainerOutputLimitError),
    ],
)
def test_container_is_removed_after_execution_failure(monkeypatch, failure, expected):
    runner = DockerRunner()
    removed = []
    monkeypatch.setattr(runner, "_check_docker", lambda: None)

    def fail(*_args):
        raise failure

    monkeypatch.setattr(runner, "_run_bounded", fail)
    monkeypatch.setattr(runner, "_remove_container", removed.append)
    with pytest.raises(expected):
        runner.execute("def add(a, b): return a + b", "add", _cases())
    assert len(removed) == 1


def test_cleanup_nonzero_exit_is_reported(monkeypatch):
    runner = DockerRunner()
    command_seen = []

    def failed_remove(command, **_kwargs):
        command_seen.append(command)
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(runner_module.subprocess, "run", failed_remove)
    with pytest.raises(ContainerCleanupError):
        runner._remove_container("pce-run-test")
    assert command_seen == [
        ["docker", "rm", "--force", "pce-run-test"],
        [
            "docker",
            "container",
            "ls",
            "--all",
            "--filter",
            "name=pce-run-test",
            "--format",
            "{{.Names}}",
        ],
    ]


def test_cleanup_accepts_container_already_removed_by_docker(monkeypatch):
    runner = DockerRunner()
    calls = []

    def auto_removed(command, **_kwargs):
        calls.append(command)
        if command[1:3] == ["rm", "--force"]:
            return subprocess.CompletedProcess(command, 1)
        return subprocess.CompletedProcess(command, 0, stdout=b"")

    monkeypatch.setattr(runner_module.subprocess, "run", auto_removed)
    runner._remove_container("pce-run-already-gone")
    assert len(calls) == 2


def test_cleanup_failure_after_success_is_not_returned_as_success(monkeypatch):
    runner = DockerRunner()
    monkeypatch.setattr(runner, "_check_docker", lambda: None)
    monkeypatch.setattr(
        runner,
        "_run_bounded",
        lambda *_args: (
            0,
            b'{"results":[{"case_number":1,"status":"returned","actual":5,"duration_ms":2}]}',
            b"",
        ),
    )

    def failed_remove(_name):
        raise ContainerCleanupError("cleanup failed")

    monkeypatch.setattr(runner, "_remove_container", failed_remove)
    with pytest.raises(ContainerCleanupError):
        runner.execute("def add(a, b): return a + b", "add", _cases())


def test_bounded_process_capture_limits_output_and_time():
    runner = DockerRunner()
    # This is a fixed local helper-process test, not submitted user code and not
    # a substitute for the Docker integration test.
    code = "import sys; sys.stdout.buffer.write(b'x' * 4096)"
    original_limit = runner_module.MAX_CONTAINER_STDOUT_BYTES
    runner_module.MAX_CONTAINER_STDOUT_BYTES = 128
    try:
        with pytest.raises(ContainerOutputLimitError):
            runner._run_bounded([sys.executable, "-c", code], b"", 2)
    finally:
        runner_module.MAX_CONTAINER_STDOUT_BYTES = original_limit

    with pytest.raises(ContainerTimedOutError):
        runner._run_bounded(
            [sys.executable, "-c", "import time; time.sleep(2)"], b"", 0.05
        )


def test_oversized_source_is_rejected_before_docker(monkeypatch):
    runner = DockerRunner()
    monkeypatch.setattr(
        runner,
        "_check_docker",
        lambda: pytest.fail("Docker must not be checked for an invalid payload"),
    )
    with pytest.raises(ValueError, match="Source code"):
        runner.execute("x" * (32 * 1024 + 1), "add", _cases())
