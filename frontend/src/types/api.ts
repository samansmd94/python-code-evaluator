export type Difficulty = "beginner" | "intermediate" | "advanced";

export interface ExerciseExample {
  input: unknown[];
  output: unknown;
}

export interface Exercise {
  id: number;
  slug: string;
  title: string;
  description: string;
  function_name: string;
  function_signature: string;
  difficulty: Difficulty;
  requirements: string[];
  examples: ExerciseExample[];
  created_at: string;
}

export interface TestSuite {
  id: number;
  slug: string;
  exercise_slug: string;
  name: string;
  description: string;
  version: number;
  case_count: number;
  created_at: string;
}

export interface TestCase {
  id: number;
  test_suite_id: number;
  case_number: number;
  input_data: unknown[];
  expected_output: unknown;
  created_at: string;
}

export interface ExerciseSuiteDetails extends TestSuite {
  cases: TestCase[];
}
