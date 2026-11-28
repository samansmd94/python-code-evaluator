"""Model relationship, constraint, and seed checks."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from backend.app.database import create_database_engine, create_session_factory
from backend.app.models import (
    Exercise,
    TestCase as TestCaseModel,
    TestSuite as TestSuiteModel,
)
from backend.app.seed import PROJECT_ROOT, seed_initial_data


def test_models_are_related_and_seeded_from_existing_cases(migrated_database):
    engine = create_database_engine(migrated_database)
    factory = create_session_factory(engine)
    try:
        with factory() as session:
            seed_initial_data(session)
            exercise = session.scalar(
                select(Exercise).where(Exercise.slug == "addition")
            )
            assert exercise is not None
            assert exercise.function_name == "add"
            assert len(exercise.test_suites) == 1
            suite = exercise.test_suites[0]
            assert suite.version == 1
            assert len(suite.test_cases) == 4
            assert suite.test_cases[0].input_data == [2, 3]
            assert suite.test_cases[0].expected_output == 5

            # The legacy file remains unchanged and retains its demonstration
            # mismatch; only the web catalog uses the corrected official file.
            from evaluator.loader import load_test_cases

            legacy_cases = load_test_cases(PROJECT_ROOT / "test_cases" / "addition.json")
            assert legacy_cases[-1] == {"input": [2, 3], "expected": 10}
    finally:
        engine.dispose()


def test_seed_is_idempotent(migrated_database):
    engine = create_database_engine(migrated_database)
    factory = create_session_factory(engine)
    try:
        with factory() as session:
            seed_initial_data(session)
            seed_initial_data(session)
            assert session.scalar(select(func.count(Exercise.id))) == 3
            assert session.scalar(select(func.count(TestSuiteModel.id))) == 3
            assert session.scalar(select(func.count(TestCaseModel.id))) == 10
    finally:
        engine.dispose()


def test_seed_repairs_existing_records_from_official_files(migrated_database):
    engine = create_database_engine(migrated_database)
    factory = create_session_factory(engine)
    try:
        with factory() as session:
            seed_initial_data(session)
            suite = session.scalar(
                select(TestSuiteModel).where(
                    TestSuiteModel.slug == "addition-default-v1"
                )
            )
            assert suite is not None
            first_case = next(
                case for case in suite.test_cases if case.case_number == 1
            )
            first_case.expected_output = 10
            session.add(
                TestCaseModel(
                    test_suite_id=suite.id,
                    case_number=99,
                    input_data=[1, 1],
                    expected_output=2,
                )
            )
            division = session.scalar(
                select(Exercise).where(Exercise.slug == "division")
            )
            assert division is not None
            division.description = "stale seed description"
            session.commit()

            seed_initial_data(session)

            addition_cases = list(
                session.scalars(
                    select(TestCaseModel)
                    .where(TestCaseModel.test_suite_id == suite.id)
                    .order_by(TestCaseModel.case_number)
                )
            )
            assert len(addition_cases) == 4
            assert addition_cases[0].expected_output == 5
            division = session.scalar(
                select(Exercise).where(Exercise.slug == "division")
            )
            assert division is not None
            assert "Return None" in division.description
            assert session.scalar(select(func.count(Exercise.id))) == 3
            assert session.scalar(select(func.count(TestSuiteModel.id))) == 3
            assert session.scalar(select(func.count(TestCaseModel.id))) == 10
    finally:
        engine.dispose()


def test_official_expected_results_match_the_exercise_contract(migrated_database):
    from evaluator.comparator import compare_results
    from evaluator.engine import evaluate
    from exercises.basic_exercises import add, divide, greet

    reference_functions = {"addition": add, "division": divide, "greeting": greet}
    engine = create_database_engine(migrated_database)
    factory = create_session_factory(engine)
    try:
        with factory() as session:
            seed_initial_data(session)
            suites = session.scalars(
                select(TestSuiteModel).order_by(TestSuiteModel.slug)
            ).all()
            for suite in suites:
                cases = sorted(suite.test_cases, key=lambda case: case.case_number)
                for case in cases:
                    if suite.exercise.slug == "division" and case.input_data[1] == 0:
                        assert case.expected_output is None
                        assert any(
                            "Return None" in requirement
                            for requirement in suite.exercise.requirements
                        )
                        # The legacy trusted function raises here; that remains
                        # an execution error rather than a passing evaluation.
                        legacy_result = evaluate(
                            divide,
                            [{"input": case.input_data, "expected": None}],
                        )[0]
                        assert legacy_result["status"] == "error"
                        assert legacy_result["passed"] is False
                        continue

                    actual = reference_functions[suite.exercise.slug](*case.input_data)
                    assert compare_results(actual, case.expected_output)
    finally:
        engine.dispose()


def test_database_constraints_reject_duplicate_case_numbers(migrated_database):
    engine = create_database_engine(migrated_database)
    factory = create_session_factory(engine)
    try:
        with factory() as session:
            seed_initial_data(session)
            suite = session.scalar(
                select(TestSuiteModel).where(
                    TestSuiteModel.slug == "greeting-default-v1"
                )
            )
            assert suite is not None
            session.add(
                TestCaseModel(
                    test_suite_id=suite.id,
                    case_number=1,
                    input_data=["Different"],
                    expected_output="Hello Different",
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()
    finally:
        engine.dispose()
