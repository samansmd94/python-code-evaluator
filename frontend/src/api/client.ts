import type { Exercise, TestCase, TestSuite } from "../types/api";

const configuredBase = import.meta.env.VITE_API_BASE_URL?.trim();
const apiBase = (configuredBase || "/api").replace(/\/$/, "");

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function getJson<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBase}${path}`, {
      headers: { Accept: "application/json" },
    });
  } catch {
    throw new ApiError("Could not reach the backend. Check that it is running.", 0);
  }

  if (!response.ok) {
    throw new ApiError(await readError(response), response.status);
  }
  return (await response.json()) as T;
}

async function readError(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (typeof body === "object" && body !== null && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string") return detail;
      if (
        typeof detail === "object" &&
        detail !== null &&
        "message" in detail &&
        typeof (detail as { message: unknown }).message === "string"
      ) {
        return (detail as { message: string }).message;
      }
    }
  } catch {
    // Use the status-based fallback for empty or non-JSON error responses.
  }
  return `The backend returned an error (${response.status}).`;
}

export function getExercises(): Promise<Exercise[]> {
  return getJson<Exercise[]>("/exercises");
}

export function getExercise(slug: string): Promise<Exercise> {
  return getJson<Exercise>(`/exercises/${encodeURIComponent(slug)}`);
}

export function getTestSuites(exerciseSlug?: string): Promise<TestSuite[]> {
  const query = exerciseSlug
    ? `?exercise_slug=${encodeURIComponent(exerciseSlug)}`
    : "";
  return getJson<TestSuite[]>(`/test-suites${query}`);
}

export function getExerciseSuites(slug: string): Promise<TestSuite[]> {
  return getJson<TestSuite[]>(
    `/exercises/${encodeURIComponent(slug)}/test-suites`,
  );
}

export function getTestCases(suiteSlug: string): Promise<TestCase[]> {
  return getJson<TestCase[]>(
    `/test-suites/${encodeURIComponent(suiteSlug)}/test-cases`,
  );
}
