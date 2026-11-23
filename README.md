# Python Code Evaluator

A lightweight Python function evaluation tool that executes trusted Python functions against predefined test cases and generates detailed evaluation reports.

## Overview

Python Code Evaluator is a modular project designed to evaluate Python functions using structured test cases.

It supports:
- Executing Python functions with different arguments.
- Comparing actual results with expected results.
- Handling execution errors and exceptions.
- Loading test cases from JSON files.
- Validating test-case structures.
- Generating individual evaluation reports.
- Generating combined evaluation summaries.
- Automated testing with pytest.

## Project Status

**Currently under development.**

The current version evaluates trusted Python functions defined within the project.

An important future development goal is to support user-submitted Python code.

This will require additional security and execution-isolation capabilities, including appropriate sandboxing, resource restrictions, execution time limits, and protection against unauthorized access to files and system resources.

The current implementation is **not a secure sandbox** and must not be used to execute untrusted code.

## Project Structure

```text
python-code-evaluator/
│
├── evaluator/
│   ├── __init__.py
│   ├── runner.py
│   ├── comparator.py
│   ├── engine.py
│   ├── reporter.py
│   └── loader.py
│
├── exercises/
│   ├── __init__.py
│   └── basic_exercises.py
│
├── test_cases/
│   ├── addition.json
│   ├── division.json
│   └── greeting.json
│
├── tests/
│   ├── test_comparator.py
│   ├── test_engine.py
│   ├── test_loader.py
│   ├── test_reporter.py
│   └── test_runner.py
│
├── main.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Technologies

- Python
- JSON
- pytest
- Git

## Installation

Clone the repository:

```bash
git clone https://github.com/samansmd94/python-code-evaluator.git
cd python-code-evaluator
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the evaluator:

```bash
python main.py
```

The program loads predefined test cases from the `test_cases/` directory, evaluates the corresponding Python functions, and displays individual reports and an overall summary.

## Example Test Case

Test cases are stored in JSON format.

```json
[
    {
        "input": [2, 3],
        "expected": 5
    },
    {
        "input": [10, 20],
        "expected": 30
    }
]
```

The `input` field contains the positional arguments passed to the function, while `expected` contains the expected return value.

## Running Tests

Run the automated test suite:

```bash
python -m pytest -q
```

The project currently includes 29 automated tests covering the evaluator's core components.

## Architecture

The application is divided into separate modules:

| Module | Responsibility |
|---|---|
| `runner.py` | Executes functions and captures exceptions |
| `comparator.py` | Compares actual and expected results |
| `engine.py` | Coordinates the evaluation process |
| `reporter.py` | Generates individual and overall reports |
| `loader.py` | Loads and validates JSON test cases |

## Future Development

- Secure execution of user-submitted Python code.
- Isolated execution environments.
- Execution time and resource limits.
- More flexible test-case validation.
- Additional evaluation and reporting capabilities.
- Improved command-line interface.

## License

To be determined.
