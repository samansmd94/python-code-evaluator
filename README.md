# Python Code Evaluator

Python Code Evaluator keeps its v2.0.0 trusted-function CLI and adds a backend for a SQLite-backed exercise catalog and isolated evaluation of submitted Python functions. Submitted source runs only inside a disposable Docker container. The legacy CLI still runs trusted local functions in its own process and is not a sandbox.

## Features

- Execute registered local functions with positional arguments.
- Compare results using exact equality by default, or optional numeric tolerance (including nested lists and dictionaries).
- Distinguish passed tests, ordinary comparison failures, and execution errors.
- Load and validate JSON test-case files with case-specific error messages.
- Print per-test reports and combined summaries; export deterministic JSON to standard output.
- Use the CLI without editing `main.py`.
- Add trusted functions through a small registry API.
- Run the test suite with pytest. The legacy evaluator package uses only the Python standard library at runtime.
- Read exercise, test-suite, and official test-case data through a FastAPI backend.
- Persist the initial catalog in SQLite with SQLAlchemy and versioned Alembic migrations.
- Submit source against a known official suite and inspect per-test results and evaluation history.
- Run submissions in a fixed, locally built Docker image with a pinned Python base image and restrictive container settings.

The frontend now provides a catalog dashboard and exercise browsing. Submission editing, evaluation history lists, and analytics remain future work.

## Architecture

| Module | Responsibility |
|---|---|
| `evaluator/runner.py` | Calls one trusted function and captures ordinary exceptions. |
| `evaluator/comparator.py` | Applies exact comparison or optional numeric tolerance. |
| `evaluator/engine.py` | Coordinates execution and comparison and creates per-case results. |
| `evaluator/loader.py` | Loads JSON and validates test cases. |
| `evaluator/reporter.py` | Builds summary data, prints text reports, and serializes JSON. |
| `evaluator/registry.py` | Maps safe CLI names to explicitly trusted project functions. |
| `evaluator/cli.py` | Parses commands, runs evaluations, and sets exit codes. |
| `exercises/` | Contains the example functions that the registry exposes. |
| `backend/app/models.py` | Defines exercise, test-suite, and test-case database models. |
| `backend/app/api.py` | Serves read-only catalog and test-case endpoints plus submission and evaluation-history endpoints. |
| `backend/app/seed.py` | Imports the existing exercise descriptions and JSON cases idempotently. |
| `backend/app/execution/` | Validates execution inputs and starts/cleans up fixed-configuration Docker containers. |
| `backend/app/services/evaluation_service.py` | Coordinates trusted suite lookup, isolated execution, comparison, and history persistence. |
| `backend/execution_image/` | Contains the pinned image definition and the in-container worker. User code is loaded only inside this image. |
| `backend/migrations/versions/0002_execution_history.py` | Adds submission, evaluation-run, and per-test-result history tables. |
| `backend/migrations/` | Tracks SQLite schema changes with Alembic. |
| `backend/tests/` | Tests migrations, models, seed data, and API behavior. |
| `frontend/src/api/client.ts` | Centralizes the typed browser API requests and error handling. |
| `frontend/src/layout/` and `frontend/src/pages/` | Provide responsive navigation and the dashboard, exercise catalog/details, history, and settings pages. |

### Project structure

```text
python-code-evaluator/
├── evaluator/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── comparator.py
│   ├── engine.py
│   ├── loader.py
│   ├── registry.py
│   ├── reporter.py
│   └── runner.py
├── exercises/
│   ├── __init__.py
│   └── basic_exercises.py
├── test_cases/
├── tests/
├── backend/
│   ├── app/
│   │   ├── api.py
│   │   ├── database.py
│   │   ├── execution/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── seed.py
│   ├── migrations/
│   ├── execution_image/
│   │   ├── Dockerfile
│   │   └── worker.py
│   ├── tests/
│   ├── test_cases/official/
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── layout/
│   │   ├── pages/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
├── main.py                 # compatible all-exercises entry point
├── requirements.txt        # backend and test dependencies
└── README.md
```

## Installation

Use Python 3.10 or newer. Clone the repository and enter its directory:

```bash
git clone https://github.com/samansmd94/python-code-evaluator.git
cd python-code-evaluator
```

Create and activate a virtual environment, then install the development dependency:

```bash
python3 -m venv .venv
source .venv/bin/activate       # macOS/Linux
python -m pip install -r requirements.txt
```

The legacy evaluator package itself has no third-party runtime dependencies. The backend adds FastAPI, SQLAlchemy, and Alembic; pytest and HTTPX support automated tests.

## Backend setup

From the repository root, activate the virtual environment and install the project requirements as shown above. Apply the database migration, then start the API:

```bash
alembic -c backend/alembic.ini upgrade head
uvicorn backend.app.main:app --reload
```

On startup, the backend synchronizes the three managed exercises and corrected official test cases from `backend/test_cases/official/`. This also repairs catalog rows from the earlier Phase 2 seed; repeated seeding does not create duplicate records. The default database is `backend/data/evaluator.sqlite3`; that local data file is ignored by Git. Evaluation-history tables are created by the Alembic migration.

To use another SQLite file, set `DATABASE_URL` before both migration and startup:

```bash
export DATABASE_URL="sqlite:////absolute/path/to/evaluator.sqlite3"
alembic -c backend/alembic.ini upgrade head
uvicorn backend.app.main:app --reload
```

The API is documented at `http://127.0.0.1:8000/docs`. Catalog endpoints are read-only:

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Process health check. |
| GET | `/api/exercises` | List exercises. |
| GET | `/api/exercises/{exercise_slug}` | Get exercise details. |
| GET | `/api/exercises/{exercise_slug}/test-suites` | List an exercise's suites. |
| GET | `/api/test-suites` | List suites; optional `exercise_slug` filter. |
| GET | `/api/test-suites/{suite_slug}` | Get suite details and case count. |
| GET | `/api/test-suites/{suite_slug}/test-cases` | List official test cases in order. |
| POST | `/api/submissions` | Evaluate submitted source against a named official suite. |
| GET | `/api/evaluations/{evaluation_id}` | Retrieve a saved evaluation report. |

There is no API route for changing official cases, and submission requests cannot provide a function name, test inputs, or Docker settings.

### Docker execution setup

Install and start Docker Desktop (or a compatible Docker Engine), then build the fixed execution image from the repository root:

```bash
docker build -f backend/execution_image/Dockerfile \\
  -t python-code-evaluator-execution:3.14.7-v1 backend/execution_image
```

The image uses the Python 3.14.7 slim Bookworm image pinned by digest. The API checks for this local image and does not pull or substitute another image. If Docker or the image is unavailable, submission requests return a safe `503` response; there is no in-process fallback.

With the API running, submit a solution using the suite slug:

```bash
curl -X POST http://127.0.0.1:8000/api/submissions \\
  -H 'Content-Type: application/json' \\
  -d '{"test_suite_slug":"addition-default-v1","source_code":"def add(a, b):\\n    return a + b\\n"}'
```

The JSON response includes the evaluation and submission IDs, status, passed/failed/error counts, success rate, elapsed time, and individual case results. Retrieve it later with `GET /api/evaluations/{evaluation_id}`. The complete submission request body is limited to 256 KiB before JSON parsing, source is limited to 32 KiB, and suites are limited to 50 cases. Per-case and whole-run timeouts, output caps, and container resource limits are enforced by the execution configuration.

Possible run statuses are `completed`, `invalid_submission`, `timed_out`, `infrastructure_error`, and `internal_error`. A wrong return value is `failed`; syntax errors, missing functions, runtime errors, timeouts, and output-limit events are separately reported as test errors. Infrastructure failures are recorded and returned as a safe service error with the evaluation ID. Unexpected internal evaluation failures are saved as a terminal `internal_error` report without exposing exception details.

Run backend and evaluator tests together with `python -m pytest -q`.

## Frontend setup

The frontend uses React, TypeScript, Vite, Tailwind CSS, React Router, and Lucide icons. It reads exercise, suite, and official case data from the existing backend. From a separate terminal at the repository root:

```bash
cd frontend
pnpm install
pnpm dev
```

Vite serves the frontend at `http://localhost:5173` and proxies `/api` and `/health` to `http://127.0.0.1:8000`; this same-origin proxy means development does not require CORS. The default API base is `/api`. To use another API origin, copy `.env.example` to `.env.local`, set `VITE_API_BASE_URL` to that API's `/api` URL, and set the backend's `CORS_ORIGINS` environment variable to the exact frontend origin (for example, `http://localhost:5173`). CORS is disabled unless origins are explicitly configured.

The Dashboard displays only live exercise, suite, and official-case counts. The current backend has no trend or aggregate analytics endpoints, so no charts or performance figures are fabricated. Recharts is deferred until real time-series data is available. Evaluation History explains that only ID-based report retrieval exists; Settings is a clear placeholder. The code editor and submission UI are not part of this phase.

Create a production bundle and run frontend tests from `frontend/`:

```bash
pnpm build
pnpm test
```

### Legacy and official test data

The legacy CLI continues to use the original files in `test_cases/`. Those files are unchanged, including their demonstration mismatch and division-by-zero execution error. The web catalog seeds from separate files in `backend/test_cases/official/`: addition correctly expects `5` for `[2, 3]`, and the division exercise explicitly requires returning `None` when the divisor is zero. An execution exception remains an error and is not counted as a pass.

## Usage

Run one registered function and its test file:

```bash
python -m evaluator run --function add --tests test_cases/addition.json
```

Other registered functions are `divide` and `greet`:

```bash
python -m evaluator run --function greet --tests test_cases/greeting.json
python -m evaluator run --function divide --tests test_cases/division.json
```

Use `--format json` to write a machine-readable report to standard output. Add `--tolerance` to allow small numeric differences:

```bash
python -m evaluator run --function add --tests test_cases/addition.json --format json
python -m evaluator run --function divide --tests test_cases/division.json --tolerance 0.000001
```

Get command help with:

```bash
python -m evaluator --help
python -m evaluator run --help
```

`python main.py` remains available and runs the three example evaluations together.

### Exit codes

- `0`: all test cases passed.
- `1`: at least one test failed or raised an execution error.
- `2`: invalid CLI arguments or an input file could not be loaded.

An invalid function name is rejected by the CLI's registered choices; user-provided names are never imported or evaluated dynamically.

## JSON test-case format

The root must be a non-empty array. Each item must contain exactly `input` and `expected`. `input` is a non-empty array of positional arguments. `expected` may be any standard JSON value: `null`, a string, number, boolean, array, or object. Values nested inside inputs and expected results must also be JSON values.

```json
[
  {"input": [2, 3], "expected": 5},
  {"input": [10, 20], "expected": 30}
]
```

Unexpected fields, missing fields, invalid JSON, empty files, and empty case arrays are reported as input errors. Empty `input` arrays are rejected to match the original format; functions that take no arguments can still be evaluated directly through the Python API.

## Results and example output

Each evaluation result contains `input`, `expected`, `actual`, `passed`, `error`, `status`, and `test_number`. `status` is `passed`, `failed`, or `error`; Each test is counted in exactly one category: passed, failed, or error. Execution errors are reported separately and are not included in the failed count.

Text output includes each case and a summary. A successful run ends with a summary like:

```text
Total tests: 2
Passed: 2
Failed: 0
Errors: 0
Success rate: 100.00%
```

JSON output is a stable object with `total`, `passed`, `failed`, `errors`, `success_rate`, and `results` fields. It is intended for other tools to consume.

## Add a trusted function

Define the function in project code and add it to the registry in
`evaluator/registry.py`. The CLI's choices are built from that registry:

```python
from exercises.my_exercises import my_function
from evaluator.registry import register_function

register_function("my_function", my_function)
```

For applications embedding the evaluator, `register_function(name, function)`
provides the same registration API. Only add functions you trust.

## Error handling and logging

The legacy runner catches ordinary exceptions raised while calling a trusted function, returns the error message, and logs a warning with the function name and error. The submission service returns safe categories for worker errors and does not expose container output or internal exception details. It keeps the distinction between an execution error and a result that simply did not match. Invalid test files produce clear `ValueError` or `FileNotFoundError` messages; the CLI displays those as concise errors and exits with code 2. Reports go to standard output, while logs and CLI errors go to standard error.

## Automated tests

Run all automated tests from the project root:

```bash
python -m pytest -q
```

The suite covers execution, comparison, evaluation, loader validation, reporting, registry-backed CLI behavior, backend API and persistence, request-body limits, and Docker runner configuration/cleanup. Docker interactions are mocked in regular unit/API tests, so the normal suite does not require a Docker daemon.

To run the optional real-container integration test, build the fixed image as shown above, ensure Docker is running, then run:

```bash
RUN_DOCKER_INTEGRATION=1 python -m pytest -q backend/tests/test_docker_integration.py
```

The integration tests run real submissions in disposable containers. They cover result-serializer monkeypatching, source syntax errors versus runtime `SyntaxError`, runtime failures, timeouts, and container removal. Without the environment variable, pytest skips these tests.

## Limitations and security considerations

The backend does not use `eval()` or `exec()` to run submitted code in the FastAPI process. It passes a bounded request to a fixed local Docker image. Inside the container, a supervisor launches a fresh Python child for each test. The child output is treated as untrusted data; the supervisor validates it, assigns the outcome status, and builds the structured response. Official expected values stay in the backend, where comparison happens. The separate process helps keep module changes such as a `json.dumps` monkeypatch away from the supervisor, but process separation alone is not a complete security boundary.

Each container has no network, uses a non-root user, a read-only root filesystem with a restricted temporary directory, dropped Linux capabilities, no-new-privileges, and fixed CPU, memory, process-count, file, output, and time limits. The container receives only source, a trusted function name, and official inputs; it has no host mounts, project directory, Docker socket, database, or application credentials. Containers are automatically removed on exit and explicitly removed by the runner. A cleanup failure is logged; if execution otherwise succeeded, it is returned as an infrastructure error.

Docker isolation reduces risk but is not an absolute security boundary, and this project is not production-grade hostile-code isolation. Container-runtime or kernel vulnerabilities, configuration mistakes, denial-of-service attempts, and resource contention remain possible. Do not expose this local single-user application to the public internet or treat it as a secure multi-tenant execution service. A production service would need a hardened, separately managed isolation layer or execution service, stronger tenant separation, monitoring, operational controls, and ongoing security review. The legacy CLI remains for trusted, project-defined functions only; it executes in-process and must never be used for arbitrary submitted code.

## Roadmap

- Add broader examples for validation and comparison behavior.
- Consider richer output destinations and summary formats if users need them.
- Add operational monitoring and review hardened isolation options before considering public or multi-user hosting.

The current API can evaluate submitted code only through the fixed Docker execution path described above. The trusted CLI remains a separate in-process tool.

## License

To be determined.
