"""Idempotently seed the database from the official web test catalog."""

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from evaluator.loader import load_test_cases

from .database import create_database_engine, create_session_factory, get_database_url
from .models import Exercise, TestCase, TestSuite

PROJECT_ROOT = Path(__file__).resolve().parents[2]

EXERCISE_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "slug": "addition",
        "title": "Add Two Numbers",
        "description": "Return the sum of two numeric values.",
        "function_name": "add",
        "function_signature": "add(a, b)",
        "difficulty": "beginner",
        "requirements": [
            "Accept two positional numeric arguments.",
            "Return their arithmetic sum.",
        ],
        "examples": [{"input": [2, 3], "output": 5}],
        "suite_slug": "addition-default-v1",
        "suite_name": "Addition Test Suite",
        "suite_description": "Corrected official addition cases for the web catalog.",
        "test_file": "addition.json",
    },
    {
        "slug": "division",
        "title": "Divide Two Numbers",
        "description": (
            "Return the quotient of two numbers. Return None when the divisor is zero."
        ),
        "function_name": "divide",
        "function_signature": "divide(a, b)",
        "difficulty": "beginner",
        "requirements": [
            "Accept two positional numeric arguments.",
            "Return the quotient of the first argument divided by the second.",
            "Return None when the second argument is zero.",
        ],
        "examples": [
            {"input": [10, 2], "output": 5},
            {"input": [10, 0], "output": None},
        ],
        "suite_slug": "division-default-v1",
        "suite_name": "Division Test Suite",
        "suite_description": "Official division cases; a zero divisor returns None.",
        "test_file": "division.json",
    },
    {
        "slug": "greeting",
        "title": "Create a Greeting",
        "description": "Return a greeting for the supplied name.",
        "function_name": "greet",
        "function_signature": "greet(name)",
        "difficulty": "beginner",
        "requirements": [
            "Accept one name as a positional argument.",
            "Return the text 'Hello ' followed by the name.",
        ],
        "examples": [{"input": ["Sam"], "output": "Hello Sam"}],
        "suite_slug": "greeting-default-v1",
        "suite_name": "Greeting Test Suite",
        "suite_description": "Official greeting cases for the web catalog.",
        "test_file": "greeting.json",
    },
)


def seed_initial_data(session: Session) -> None:
    """Synchronize the managed catalog to its source-controlled definitions."""
    for definition in EXERCISE_CATALOG:
        exercise = session.scalar(
            select(Exercise).where(Exercise.slug == definition["slug"])
        )
        if exercise is None:
            exercise = Exercise(
                slug=definition["slug"],
                title=definition["title"],
                description=definition["description"],
                function_name=definition["function_name"],
                function_signature=definition["function_signature"],
                difficulty=definition["difficulty"],
                requirements=definition["requirements"],
                examples=definition["examples"],
            )
            session.add(exercise)
            session.flush()
        else:
            exercise.title = definition["title"]
            exercise.description = definition["description"]
            exercise.function_name = definition["function_name"]
            exercise.function_signature = definition["function_signature"]
            exercise.difficulty = definition["difficulty"]
            exercise.requirements = definition["requirements"]
            exercise.examples = definition["examples"]

        suite = session.scalar(
            select(TestSuite).where(TestSuite.slug == definition["suite_slug"])
        )
        if suite is None:
            suite = TestSuite(
                slug=definition["suite_slug"],
                exercise_id=exercise.id,
                name=definition["suite_name"],
                description=definition["suite_description"],
                version=1,
            )
            session.add(suite)
            session.flush()
        else:
            suite.exercise_id = exercise.id
            suite.name = definition["suite_name"]
            suite.description = definition["suite_description"]
            suite.version = 1

        test_cases = load_test_cases(
            PROJECT_ROOT
            / "backend"
            / "test_cases"
            / "official"
            / definition["test_file"]
        )
        expected_case_numbers = set()
        for case_number, test_case in enumerate(test_cases, start=1):
            expected_case_numbers.add(case_number)
            existing_case = session.scalar(
                select(TestCase).where(
                    TestCase.test_suite_id == suite.id,
                    TestCase.case_number == case_number,
                )
            )
            if existing_case is None:
                session.add(
                    TestCase(
                        test_suite_id=suite.id,
                        case_number=case_number,
                        input_data=test_case["input"],
                        expected_output=test_case["expected"],
                    )
                )
            else:
                existing_case.input_data = test_case["input"]
                existing_case.expected_output = test_case["expected"]

        for existing_case in session.scalars(
            select(TestCase).where(TestCase.test_suite_id == suite.id)
        ):
            if existing_case.case_number not in expected_case_numbers:
                session.delete(existing_case)

    session.commit()


def seed_database(database_url: str | None = None) -> None:
    """Open the configured database and seed its catalog."""
    engine = create_database_engine(database_url or get_database_url())
    factory = create_session_factory(engine)
    try:
        with factory() as session:
            seed_initial_data(session)
    finally:
        engine.dispose()


if __name__ == "__main__":
    seed_database()
