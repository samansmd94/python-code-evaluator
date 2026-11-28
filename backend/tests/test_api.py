"""Read-only catalog API tests."""


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_and_get_exercises(client):
    response = client.get("/api/exercises")
    assert response.status_code == 200
    exercises = response.json()
    assert len(exercises) == 3
    addition = next(item for item in exercises if item["slug"] == "addition")
    assert addition["difficulty"] == "beginner"
    assert addition["function_signature"] == "add(a, b)"

    detail = client.get("/api/exercises/addition")
    assert detail.status_code == 200
    assert detail.json()["title"] == "Add Two Numbers"


def test_missing_exercise_returns_404(client):
    response = client.get("/api/exercises/not-an-exercise")
    assert response.status_code == 404
    assert response.json()["detail"] == "Exercise not found"


def test_suite_list_and_exercise_suite_filter(client):
    all_suites = client.get("/api/test-suites")
    assert all_suites.status_code == 200
    assert len(all_suites.json()) == 3
    addition_suites = client.get("/api/exercises/addition/test-suites")
    assert addition_suites.status_code == 200
    assert len(addition_suites.json()) == 1
    assert addition_suites.json()[0]["case_count"] == 4


def test_suite_detail_and_official_cases_are_read_only(client):
    suite = client.get("/api/test-suites/greeting-default-v1")
    assert suite.status_code == 200
    assert suite.json()["case_count"] == 2

    cases = client.get("/api/test-suites/greeting-default-v1/test-cases")
    assert cases.status_code == 200
    assert [case["case_number"] for case in cases.json()] == [1, 2]
    assert cases.json()[0]["input_data"] == ["Saman"]
    assert cases.json()[0]["expected_output"] == "Hello Saman"

    write_attempt = client.post(
        "/api/test-suites/greeting-default-v1/test-cases",
        json={"input_data": ["Changed"], "expected_output": "Changed"},
    )
    assert write_attempt.status_code == 405


def test_web_catalog_uses_corrected_official_cases(client):
    addition = client.get("/api/test-suites/addition-default-v1/test-cases").json()
    assert len(addition) == 4
    assert addition[0]["input_data"] == [2, 3]
    assert addition[0]["expected_output"] == 5

    division = client.get("/api/test-suites/division-default-v1/test-cases").json()
    zero_division = next(case for case in division if case["input_data"] == [10, 0])
    assert zero_division["expected_output"] is None


def test_unknown_suite_and_exercise_filter_return_404(client):
    assert client.get("/api/test-suites/unknown-suite").status_code == 404
    assert client.get("/api/test-suites?exercise_slug=unknown").status_code == 404
