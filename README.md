# Python Code Evaluator

Python Code Evaluator is a small tool for evaluating **trusted, locally defined Python functions** against JSON test cases. Version 2.0.0 adds a registry-based command line, stronger test-case validation, optional numeric tolerance, structured reports, and clearer error states.

> **Security:** This project is not a sandbox. It must only execute functions that you trust and that are defined as part of the project. Do not use it to run arbitrary code supplied by users.

## Features

- Execute registered local functions with positional arguments.
- Compare results using exact equality by default, or optional numeric tolerance (including nested lists and dictionaries).
- Distinguish passed tests, ordinary comparison failures, and execution errors.
- Load and validate JSON test-case files with case-specific error messages.
- Print per-test reports and combined summaries; export deterministic JSON to standard output.
- Use the CLI without editing `main.py`.
- Add trusted functions through a small registry API.
- Run the test suite with pytest. Runtime code uses only the Python standard library.

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
├── main.py                 # compatible all-exercises entry point
├── requirements.txt        # pytest for development
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

The evaluator itself has no third-party runtime dependencies. `requirements.txt` contains pytest for development.

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

The runner catches ordinary exceptions raised while calling a function, returns the error message, and logs a warning with the function name and error. It does not hide the distinction between an execution error and a result that simply did not match. Invalid test files produce clear `ValueError` or `FileNotFoundError` messages; the CLI displays those as concise errors and exits with code 2. Reports go to standard output, while logs and CLI errors go to standard error.

## Automated tests

Run all automated tests from the project root:

```bash
python -m pytest -q
```

The suite covers execution, comparison, evaluation, loader validation, reporting, registry-backed CLI behavior, and a module-command integration path.

## Limitations and security considerations

This version calls Python functions in the same process as the evaluator. Exception handling only reports ordinary failures; it does not prevent a function from accessing files, using the network, consuming excessive CPU or memory, changing process state, or terminating the process. A subprocess by itself, restricted built-ins, and a hand-built Python sandbox do not make arbitrary Python code safe.

Do not expose this application as a service that accepts and runs untrusted code. If that becomes a requirement, use a separately isolated execution service or an established isolation technology. A safe design needs strong process or machine isolation, strict time and resource limits, restricted filesystem access, disabled or controlled network access, and careful handling of communication between the evaluator and the isolated worker. Those protections are outside this project's current scope.

## Roadmap

- Add broader examples for validation and comparison behavior.
- Consider richer output destinations and summary formats if users need them.
- Research an established isolated execution service before considering any untrusted-code feature.

No untrusted-code execution or sandbox is planned as part of the current application.

## License

To be determined.
