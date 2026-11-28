import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  ArrowRight,
  BookOpenCheck,
  CheckCircle2,
  ClipboardList,
  FlaskConical,
} from "lucide-react";
import { Link } from "react-router-dom";
import { ApiError, getExercises, getTestSuites } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { StatePanel } from "../components/StatePanel";
import type { Exercise, TestSuite } from "../types/api";

export function DashboardPage() {
  const [catalog, setCatalog] = useState<{
    exercises: Exercise[];
    suites: TestSuite[];
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([getExercises(), getTestSuites()])
      .then(([exercises, suites]) => {
        if (active) setCatalog({ exercises, suites });
      })
      .catch((cause: unknown) => {
        if (!active) return;
        setError(
          cause instanceof ApiError
            ? cause.message
            : "The catalog could not be loaded.",
        );
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <>
      <PageHeader
        eyebrow="Workspace overview"
        title="Dashboard"
        description="A live overview of the exercise catalog and official test suites."
      />

      {error ? (
        <StatePanel
          kind="error"
          title="Catalog unavailable"
          message={error}
          action={
            <button className="button-secondary" onClick={() => window.location.reload()}>
              Try again
            </button>
          }
        />
      ) : catalog === null ? (
        <StatePanel
          kind="loading"
          title="Loading workspace"
          message="Retrieving the exercise catalog from the backend."
        />
      ) : catalog.exercises.length === 0 ? (
        <StatePanel
          kind="empty"
          title="No exercises yet"
          message="The backend catalog is empty. Add an exercise to the official catalog to see it here."
        />
      ) : (
        <>
          <section className="welcome-panel">
            <div className="welcome-copy">
              <span className="welcome-kicker">Catalog snapshot</span>
              <h2>Build confidence, one test at a time.</h2>
              <p>
                Explore the available Python exercises and inspect the official
                cases that define each one.
              </p>
              <Link to="/exercises" className="button-light">
                Browse exercises <ArrowRight size={16} />
              </Link>
            </div>
            <div className="welcome-art" aria-hidden="true">
              <div className="welcome-art-square square-one" />
              <div className="welcome-art-square square-two" />
              <div className="welcome-art-square square-three" />
              <Code2Graphic />
            </div>
          </section>

          <section className="stats-grid" aria-label="Live catalog counts">
            <CatalogStat
              label="Exercises"
              value={catalog.exercises.length}
              detail="Available in the catalog"
              icon={<BookOpenCheck size={19} />}
              tone="blue"
            />
            <CatalogStat
              label="Test suites"
              value={catalog.suites.length}
              detail="Official versioned suites"
              icon={<FlaskConical size={19} />}
              tone="violet"
            />
            <CatalogStat
              label="Official test cases"
              value={catalog.suites.reduce((total, suite) => total + suite.case_count, 0)}
              detail="Across the listed suites"
              icon={<ClipboardList size={19} />}
              tone="green"
            />
          </section>

          <section className="dashboard-lower-grid">
            <div className="surface-card catalog-card">
              <div className="card-heading-row">
                <div>
                  <p className="eyebrow">Getting started</p>
                  <h2>Explore your catalog</h2>
                </div>
                <span className="card-icon-circle">
                  <CheckCircle2 size={18} />
                </span>
              </div>
              <p className="card-body-copy">
                Exercise descriptions, function signatures, examples, and
                official expected results are loaded from the backend.
              </p>
              <div className="dashboard-exercise-list">
                {catalog.exercises.slice(0, 3).map((exercise) => (
                  <Link
                    key={exercise.id}
                    to={`/exercises/${encodeURIComponent(exercise.slug)}`}
                    className="dashboard-exercise-row"
                  >
                    <span className="exercise-row-mark">
                      {exercise.function_name.slice(0, 1).toUpperCase()}
                    </span>
                    <span className="exercise-row-text">
                      <strong>{exercise.title}</strong>
                      <code>{exercise.function_signature}</code>
                    </span>
                    <ArrowRight size={16} />
                  </Link>
                ))}
              </div>
              {catalog.exercises.length > 3 ? (
                <Link to="/exercises" className="text-link mt-4">
                  View all {catalog.exercises.length} exercises <ArrowRight size={15} />
                </Link>
              ) : null}
            </div>

            <div className="surface-card insight-placeholder">
              <span className="placeholder-icon">
                <ClipboardList size={20} />
              </span>
              <p className="eyebrow">Evaluation insights</p>
              <h2>History analytics are not available yet</h2>
              <p className="card-body-copy">
                This backend provides individual evaluation reports, but does
                not yet provide a history feed or trend data. No performance
                figures are shown until those records can be queried.
              </p>
              <Link to="/history" className="text-link mt-5">
                About evaluation history <ArrowRight size={15} />
              </Link>
            </div>
          </section>
        </>
      )}
    </>
  );
}

function CatalogStat({
  label,
  value,
  detail,
  icon,
  tone,
}: {
  label: string;
  value: number;
  detail: string;
  icon: ReactNode;
  tone: "blue" | "violet" | "green";
}) {
  return (
    <article className="surface-card stat-card" aria-label={`${label}: ${value}`}>
      <div className="stat-topline">
        <span>{label}</span>
        <span className={`stat-icon stat-icon-${tone}`}>{icon}</span>
      </div>
      <strong className="stat-value">{value}</strong>
      <span className="stat-detail">{detail}</span>
    </article>
  );
}

function Code2Graphic() {
  return (
    <div className="code-graphic">
      <span />
      <span />
      <span />
      <span />
      <span />
    </div>
  );
}
