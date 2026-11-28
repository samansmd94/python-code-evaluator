"""Fixed-configuration Docker runner for untrusted Python submissions."""

import json
import logging
import os
import signal
import subprocess
import threading
import time
from typing import Any, Sequence
from uuid import uuid4

from .limits import (
    CLEANUP_TIMEOUT_SECONDS,
    DOCKER_CHECK_TIMEOUT_SECONDS,
    EXECUTION_IMAGE,
    MAX_CASES_PER_RUN,
    MAX_CONTAINER_STDERR_BYTES,
    MAX_CONTAINER_STDOUT_BYTES,
    MAX_RUNNER_INPUT_BYTES,
    MAX_SOURCE_BYTES,
    RUN_TIMEOUT_SECONDS,
)
from .protocol import CaseExecution, CaseInput, WorkerResponse

logger = logging.getLogger(__name__)


class ExecutionInfrastructureError(Exception):
    """Base class for failures outside an individual submitted test."""


class DockerUnavailableError(ExecutionInfrastructureError):
    """Docker CLI or its daemon cannot be reached."""


class RunnerImageUnavailableError(ExecutionInfrastructureError):
    """The fixed execution image has not been built locally."""


class ContainerFailureError(ExecutionInfrastructureError):
    """The container did not return a valid worker response."""


class ContainerTimedOutError(ExecutionInfrastructureError):
    """The overall container run exceeded its fixed wall-clock limit."""


class ContainerOutputLimitError(ExecutionInfrastructureError):
    """The container exceeded the backend's captured output limit."""


class ContainerCleanupError(ExecutionInfrastructureError):
    """The Docker daemon did not confirm removal of an execution container."""


class DockerRunner:
    """Run a suite in a disposable container using only fixed Docker options."""

    def __init__(
        self,
        *,
        docker_binary: str = "docker",
        image: str = EXECUTION_IMAGE,
        run_timeout_seconds: float = RUN_TIMEOUT_SECONDS,
    ) -> None:
        # These are server configuration values, never request fields.
        self._docker_binary = docker_binary
        self._image = image
        self._run_timeout_seconds = run_timeout_seconds

    def execute(
        self,
        source_code: str,
        function_name: str,
        test_cases: Sequence[CaseInput],
    ) -> list[CaseExecution]:
        """Execute the submitted function separately for each trusted input."""
        self._validate_payload(source_code, function_name, test_cases)
        payload = json.dumps(
            {
                "source_code": source_code,
                "function_name": function_name,
                "test_cases": [case.model_dump() for case in test_cases],
            },
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(payload) > MAX_RUNNER_INPUT_BYTES:
            raise ValueError("Execution input exceeds the configured limit")

        self._check_docker()
        container_name = "pce-run-{}".format(uuid4().hex)
        command = self._container_command(container_name)
        execution_error: BaseException | None = None
        try:
            return_code, stdout, _stderr = self._run_bounded(
                command, payload, self._run_timeout_seconds
            )
            if return_code != 0:
                raise ContainerFailureError("Container execution failed")
            try:
                response = WorkerResponse.model_validate_json(stdout)
            except Exception as error:
                raise ContainerFailureError("Container returned an invalid response") from error
            self._validate_results(response.results, test_cases)
            return response.results
        except BaseException as error:
            execution_error = error
            raise
        finally:
            try:
                self._remove_container(container_name)
            except ContainerCleanupError:
                if execution_error is None:
                    raise

    def _validate_payload(
        self,
        source_code: str,
        function_name: str,
        test_cases: Sequence[CaseInput],
    ) -> None:
        if len(source_code.encode("utf-8")) > MAX_SOURCE_BYTES:
            raise ValueError("Source code exceeds the configured limit")
        if not function_name.isidentifier():
            raise ValueError("Function name from the exercise catalog is invalid")
        if not test_cases or len(test_cases) > MAX_CASES_PER_RUN:
            raise ValueError("Test suite has an invalid number of cases")

    def _check_docker(self) -> None:
        """Verify the daemon and fixed local image without leaking CLI output."""
        try:
            version = subprocess.run(
                [self._docker_binary, "version", "--format", "{{.Server.Version}}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=DOCKER_CHECK_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise DockerUnavailableError("Docker is unavailable") from error
        if version.returncode != 0:
            raise DockerUnavailableError("Docker is unavailable")

        try:
            image = subprocess.run(
                [self._docker_binary, "image", "inspect", self._image, "--format", "{{.Id}}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=DOCKER_CHECK_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise DockerUnavailableError("Docker is unavailable") from error
        if image.returncode != 0:
            raise RunnerImageUnavailableError("Execution image is not installed")

    def _container_command(self, container_name: str) -> list[str]:
        """Build the complete fixed command; no option comes from the request."""
        return [
            self._docker_binary,
            "run",
            "--rm",
            "--interactive",
            "--pull=never",
            "--name",
            container_name,
            "--network",
            "none",
            "--user",
            "10001:10001",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,nodev,size=16m,uid=10001,gid=10001,mode=700",
            "--memory",
            "128m",
            "--memory-swap",
            "128m",
            "--cpus",
            "0.5",
            "--pids-limit",
            "32",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges=true",
            "--ulimit",
            "nofile=64:64",
            self._image,
        ]

    def _run_bounded(
        self, command: list[str], payload: bytes, timeout_seconds: float
    ) -> tuple[int, bytes, bytes]:
        """Run Docker with bounded pipes, a deadline, and process-group cleanup."""
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
        except OSError as error:
            raise DockerUnavailableError("Docker is unavailable") from error

        stdout_data = bytearray()
        stderr_data = bytearray()
        exceeded = threading.Event()
        stdout_thread = threading.Thread(
            target=_drain_limited,
            args=(process.stdout, stdout_data, MAX_CONTAINER_STDOUT_BYTES, exceeded),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=_drain_limited,
            args=(process.stderr, stderr_data, MAX_CONTAINER_STDERR_BYTES, exceeded),
            daemon=True,
        )
        writer_thread = threading.Thread(
            target=_write_stdin,
            args=(process.stdin, payload),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()
        writer_thread.start()
        deadline = time.monotonic() + timeout_seconds
        timed_out = False
        try:
            while process.poll() is None:
                if exceeded.is_set():
                    _kill_process_group(process)
                    break
                if time.monotonic() >= deadline:
                    timed_out = True
                    _kill_process_group(process)
                    break
                time.sleep(0.01)
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            _kill_process_group(process)
            process.wait()
        finally:
            writer_thread.join(timeout=1)
            stdout_thread.join(timeout=2)
            stderr_thread.join(timeout=2)
            _close_stream(process.stdin)
            _close_stream(process.stdout)
            _close_stream(process.stderr)

        if timed_out:
            raise ContainerTimedOutError("Container execution exceeded its time limit")
        if exceeded.is_set():
            raise ContainerOutputLimitError("Container output exceeded its limit")
        return process.returncode, bytes(stdout_data), bytes(stderr_data)

    def _remove_container(self, container_name: str) -> None:
        """Force-remove a possibly still-running container after every outcome."""
        try:
            result = subprocess.run(
                [self._docker_binary, "rm", "--force", container_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=CLEANUP_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            logger.warning("Container cleanup could not be confirmed")
            raise ContainerCleanupError("Container cleanup could not be confirmed") from error

        if result.returncode == 0:
            return

        # --rm may already have removed a container that exited just before this
        # command. Confirm absence, while treating Docker daemon errors as failure.
        try:
            listing = subprocess.run(
                [
                    self._docker_binary,
                    "container",
                    "ls",
                    "--all",
                    "--filter",
                    "name={}".format(container_name),
                    "--format",
                    "{{.Names}}",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=CLEANUP_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            logger.warning("Container cleanup command returned an unsuccessful status")
            raise ContainerCleanupError("Container cleanup could not be confirmed") from error
        remaining_names = (listing.stdout or b"").decode(
            "utf-8", errors="replace"
        ).splitlines()
        if listing.returncode != 0 or container_name in remaining_names:
            logger.warning("Container cleanup command returned an unsuccessful status")
            raise ContainerCleanupError("Container cleanup could not be confirmed")

    @staticmethod
    def _validate_results(
        results: Sequence[CaseExecution], expected_cases: Sequence[CaseInput]
    ) -> None:
        result_numbers = [result.case_number for result in results]
        expected_numbers = [case.case_number for case in expected_cases]
        if sorted(result_numbers) != sorted(expected_numbers):
            raise ContainerFailureError("Container returned an incomplete result set")


def _drain_limited(stream, destination: bytearray, limit: int, exceeded: threading.Event) -> None:
    try:
        while True:
            chunk = stream.read(8192)
            if not chunk:
                return
            remaining = limit - len(destination)
            if remaining > 0:
                destination.extend(chunk[:remaining])
            if len(chunk) > remaining:
                exceeded.set()
    except (OSError, ValueError):
        return


def _write_stdin(stream, payload: bytes) -> None:
    if stream is None:
        return
    try:
        stream.write(payload)
        stream.flush()
    except (BrokenPipeError, OSError):
        pass
    finally:
        _close_stream(stream)


def _close_stream(stream) -> None:
    if stream is not None:
        try:
            stream.close()
        except OSError:
            pass


def _kill_process_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except OSError:
        process.kill()
