import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Search, SlidersHorizontal } from "lucide-react";
import { Link } from "react-router-dom";
import { ApiError, getExercises, getTestSuites } from "../api/client";
import { DifficultyBadge } from "../components/DifficultyBadge";
import { PageHeader } from "../components/PageHeader";
import { StatePanel } from "../components/StatePanel";
import type { Exercise, TestSuite } from "../types/api";

export function ExercisesPage() {
  const [exercises, setExercises] = useState<Exercise[] | null>(null);
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([getExercises(), getTestSuites()])
      .then(([exerciseData, suiteData]) => {
        if (!active) return;
        setExercises(exerciseData);
        setSuites(suiteData);
      })
      .catch((cause: unknown) => {
        if (!active) return;
        setError(
          cause instanceof ApiError ? cause.message : "Exercises could not be loaded.",
        );
      });
    return () => {
      active = false;
    };
  }, []);

  const filtered = useMemo(() => {
    const term = filter.trim().toLowerCase();
    if (!exercises || !term) return exercises ?? [];
    return exercises.filter((exercise) =>
      [exercise.title, exercise.description, exercise.function_name, exercise.difficulty]
        .join(" ")
        .toLowerCase()
        .includes(term),
    );
  }, [exercises, filter]);

  return (
    <>
      <PageHeader
        eyebrow="Practice catalog"
        title="Exercises"
        description="Browse the exercises and inspect their official requirements and test cases."
        action={
          <span className="result-count">
            <SlidersHorizontal size={15} />
            {exercises === null ? "Loading" : `${exercises.length} exercises`}
          </span>
        }
      />

      <label className="search-box">
        <Search size={18} />
        <input
          type="search"
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          placeholder="Search by title, function, or difficulty"
          aria-label="Search exercises"
        />
        <kbd>⌘ K</kbd>
      </label>

      {error ? (
        <StatePanel
          kind="error"
          title="Exercises unavailable"
          message={error}
          action={
            <button className="button-secondary" onClick={() => window.location.reload()}>
              Try again
            </button>
          }
        />
      ) : exercises === null ? (
        <StatePanel
          kind="loading"
          title="Loading exercises"
          message="Retrieving exercise definitions and suites from the backend."
        />
      ) : filtered.length === 0 ? (
        <StatePanel
          kind="empty"
          title={exercises.length === 0 ? "No exercises available" : "No matches found"}
          message={
            exercises.length === 0
              ? "The exercise catalog does not contain any entries yet."
              : "Try a different search term."
          }
        />
      ) : (
        <section className="exercise-grid" aria-label="Available exercises">
          {filtered.map((exercise) => {
            const exerciseSuites = suites.filter(
              (suite) => suite.exercise_slug === exercise.slug,
            );
            const caseCount = exerciseSuites.reduce(
              (total, suite) => total + suite.case_count,
              0,
            );
            return (
              <article className="surface-card exercise-card" key={exercise.id}>
                <div className="exercise-card-top">
                  <span className="exercise-symbol">
                    {exercise.function_name.slice(0, 1).toUpperCase()}
                  </span>
                  <DifficultyBadge difficulty={exercise.difficulty} />
                </div>
                <h2>{exercise.title}</h2>
                <p className="exercise-description">{exercise.description}</p>
                <div className="function-signature">
                  <span>Function</span>
                  <code>{exercise.function_signature}</code>
                </div>
                <div className="exercise-card-footer">
                  <span>
                    {exerciseSuites.length} {exerciseSuites.length === 1 ? "suite" : "suites"}
                    <i />
                    {caseCount} {caseCount === 1 ? "test case" : "test cases"}
                  </span>
                  <Link
                    to={`/exercises/${encodeURIComponent(exercise.slug)}`}
                    className="icon-link"
                    aria-label={`View ${exercise.title}`}
                  >
                    <ArrowRight size={17} />
                  </Link>
                </div>
              </article>
            );
          })}
        </section>
      )}
    </>
  );
}
