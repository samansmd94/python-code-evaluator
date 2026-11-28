import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import type { Exercise, TestCase, TestSuite } from "./types/api";

vi.mock("./api/client", () => ({
  ApiError: class ApiError extends Error {},
  getExercises: vi.fn(),
  getTestSuites: vi.fn(),
  getExercise: vi.fn(),
  getExerciseSuites: vi.fn(),
  getTestCases: vi.fn(),
}));

import {
  getExercises,
  getExercise,
  getExerciseSuites,
  getTestCases,
  getTestSuites,
} from "./api/client";
import { App } from "./App";

const exercise: Exercise = {
  id: 1,
  slug: "addition",
  title: "Add Two Numbers",
  description: "Return the sum of two numeric values.",
  function_name: "add",
  function_signature: "add(a, b)",
  difficulty: "beginner",
  requirements: ["Accept two numeric arguments.", "Return their sum."],
  examples: [{ input: [2, 3], output: 5 }],
  created_at: "2026-01-01T00:00:00Z",
};

const suite: TestSuite = {
  id: 1,
  slug: "addition-default-v1",
  exercise_slug: "addition",
  name: "Addition Test Suite",
  description: "Official addition cases.",
  version: 1,
  case_count: 2,
  created_at: "2026-01-01T00:00:00Z",
};

const cases: TestCase[] = [
  {
    id: 1,
    test_suite_id: 1,
    case_number: 1,
    input_data: [2, 3],
    expected_output: 5,
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: 2,
    test_suite_id: 1,
    case_number: 2,
    input_data: [-1, 1],
    expected_output: 0,
    created_at: "2026-01-01T00:00:00Z",
  },
];

function renderApp(route = "/") {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <App />
    </MemoryRouter>,
  );
}

describe("frontend foundation", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(getExercises).mockResolvedValue([]);
    vi.mocked(getTestSuites).mockResolvedValue([]);
    vi.mocked(getExercise).mockRejectedValue(new Error("Exercise was not requested"));
    vi.mocked(getExerciseSuites).mockResolvedValue([]);
    vi.mocked(getTestCases).mockResolvedValue([]);
  });

  afterEach(() => cleanup());

  it("shows dashboard counts from the backend catalog", async () => {
    vi.mocked(getExercises).mockResolvedValue([exercise]);
    vi.mocked(getTestSuites).mockResolvedValue([suite]);
    renderApp();

    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByText("Available in the catalog")).toBeInTheDocument();
    expect(screen.getByText("Official versioned suites")).toBeInTheDocument();
    expect(screen.getByText("Across the listed suites")).toBeInTheDocument();
    expect(screen.queryByText("No history list is available")).not.toBeInTheDocument();
    expect(getExercises).toHaveBeenCalledOnce();
    expect(getTestSuites).toHaveBeenCalledOnce();
  });

  it("navigates to exercise details and displays real official cases", async () => {
    vi.mocked(getExercises).mockResolvedValue([exercise]);
    vi.mocked(getTestSuites).mockResolvedValue([suite]);
    vi.mocked(getExercise).mockResolvedValue(exercise);
    vi.mocked(getExerciseSuites).mockResolvedValue([suite]);
    vi.mocked(getTestCases).mockResolvedValue(cases);
    const user = userEvent.setup();
    renderApp("/exercises");

    await user.click(await screen.findByRole("link", { name: "View Add Two Numbers" }));
    expect(await screen.findByText("Official test suites")).toBeInTheDocument();
    await user.click(screen.getByText("Addition Test Suite"));
    expect((await screen.findAllByText("Expected output")).length).toBe(2);
    expect(screen.getByText("[2,3]")).toBeInTheDocument();
    expect(screen.getAllByText("5", { selector: "code" }).length).toBeGreaterThan(0);
    expect(getExerciseSuites).toHaveBeenCalledWith("addition");
    expect(getTestCases).toHaveBeenCalledWith("addition-default-v1");
  });

  it("keeps history honest about the missing list endpoint", async () => {
    renderApp("/history");
    expect(await screen.findByText("No history list is available")).toBeInTheDocument();
    expect(getExercises).not.toHaveBeenCalled();
  });

  it("provides working sidebar navigation and a settings placeholder", async () => {
    const user = userEvent.setup();
    renderApp();
    await user.click(screen.getByRole("link", { name: /Settings/ }));
    expect(await screen.findByText("Settings are not available yet")).toBeInTheDocument();
    expect(screen.getByText("VITE_API_BASE_URL")).toBeInTheDocument();
  });

  it("shows a helpful API error state", async () => {
    vi.mocked(getExercises).mockRejectedValue(new Error("Backend offline"));
    vi.mocked(getTestSuites).mockResolvedValue([]);
    renderApp();
    expect(await screen.findByText("Catalog unavailable")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});
