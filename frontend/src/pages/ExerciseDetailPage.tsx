import { useEffect, useState } from "react";
import { ArrowLeft, Braces, Check, ChevronDown, FlaskConical } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import {
  ApiError,
  getExercise,
  getExerciseSuites,
  getTestCases,
} from "../api/client";
import { DifficultyBadge } from "../components/DifficultyBadge";
import { StatePanel } from "../components/StatePanel";
import type { Exercise, ExerciseSuiteDetails, TestSuite } from "../types/api";

interface ExerciseDetailData {
  exercise: Exercise;
  suites: ExerciseSuiteDetails[];
}

export function ExerciseDetailPage() {
  const { slug = "" } = useParams();
  const [data, setData] = useState<ExerciseDetailData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setData(null);
    setError(null);

    async function load() {
      try {
        const [exercise, suites] = await Promise.all([
          getExercise(slug),
          getExerciseSuites(slug),
        ]);
        const detailedSuites = await Promise.all(
          suites.map(async (suite: TestSuite) => ({
            ...suite,
            cases: await getTestCases(suite.slug),
          })),
        );
        if (active) setData({ exercise, suites: detailedSuites });
      } catch (cause: unknown) {
        if (!active) return;
        setError(
          cause instanceof ApiError
            ? cause.message
            : "Exercise details could not be loaded.",
        );
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, [slug]);

  if (error) {
    return (
      <>
        <Link to="/exercises" className="back-link">
          <ArrowLeft size={16} /> Back to exercises
        </Link>
        <StatePanel kind="error" title="Exercise unavailable" message={error} />
      </>
    );
  }

  if (!data) {
    return (
      <StatePanel
        kind="loading"
        title="Loading exercise"
        message="Loading the exercise definition and official test cases."
      />
    );
  }

  return (
    <>
      <Link to="/exercises" className="back-link">
        <ArrowLeft size={16} /> Back to exercises
      </Link>
      <section className="detail-hero surface-card">
        <div className="detail-title-row">
          <span className="exercise-symbol exercise-symbol-large">
            {data.exercise.function_name.slice(0, 1).toUpperCase()}
          </span>
          <div className="min-w-0">
            <div className="detail-badges">
              <DifficultyBadge difficulty={data.exercise.difficulty} />
              <span className="catalog-label">Official exercise</span>
            </div>
            <h1>{data.exercise.title}</h1>
          </div>
        </div>
        <p className="detail-description">{data.exercise.description}</p>
        <div className="detail-signature">
          <Braces size={17} />
          <span>Required signature</span>
          <code>{data.exercise.function_signature}</code>
        </div>
        <div className="detail-summary-strip">
          <div>
            <strong>{data.suites.length}</strong>
            <span>{data.suites.length === 1 ? "Test suite" : "Test suites"}</span>
          </div>
          <div>
            <strong>
              {data.suites.reduce((total, suite) => total + suite.case_count, 0)}
            </strong>
            <span>Official cases</span>
          </div>
          <div>
            <strong>{data.exercise.examples.length}</strong>
            <span>{data.exercise.examples.length === 1 ? "Example" : "Examples"}</span>
          </div>
        </div>
      </section>

      <div className="detail-content-grid">
        <section className="surface-card detail-section">
          <div className="section-heading">
            <span className="section-icon"><Check size={18} /></span>
            <div>
              <p className="eyebrow">Exercise guide</p>
              <h2>Requirements</h2>
            </div>
          </div>
          {data.exercise.requirements.length ? (
            <ul className="requirement-list">
              {data.exercise.requirements.map((requirement) => (
                <li key={requirement}>
                  <Check size={15} />
                  <span>{requirement}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted-copy">No requirements have been provided.</p>
          )}

          <div className="subsection-divider" />
          <h3 className="subsection-title">Examples</h3>
          {data.exercise.examples.length ? (
            <div className="example-list">
              {data.exercise.examples.map((example, index) => (
                <div className="example-row" key={`${index}-${JSON.stringify(example.input)}`}>
                  <span>Example {index + 1}</span>
                  <code>{data.exercise.function_name}({formatValue(example.input)})</code>
                  <ArrowLeft className="example-arrow" size={15} />
                  <code className="example-output">{formatValue(example.output)}</code>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted-copy">No examples have been provided.</p>
          )}
        </section>

        <section className="surface-card detail-section suite-section">
          <div className="section-heading">
            <span className="section-icon section-icon-purple"><FlaskConical size={18} /></span>
            <div>
              <p className="eyebrow">Read-only catalog</p>
              <h2>Official test suites</h2>
            </div>
          </div>
          {data.suites.length === 0 ? (
            <p className="muted-copy">No test suites are available for this exercise.</p>
          ) : (
            <div className="suite-list">
              {data.suites.map((suite) => (
                <details className="suite-details" key={suite.id}>
                  <summary>
                    <span className="suite-summary-icon"><FlaskConical size={16} /></span>
                    <span className="suite-summary-copy">
                      <strong>{suite.name}</strong>
                      <small>{suite.case_count} official cases · Version {suite.version}</small>
                    </span>
                    <ChevronDown size={17} className="suite-chevron" />
                  </summary>
                  <div className="suite-details-body">
                    <p>{suite.description}</p>
                    {suite.cases.map((testCase) => (
                      <div className="test-case-row" key={testCase.id}>
                        <span className="test-case-number">{testCase.case_number}</span>
                        <div>
                          <span className="test-case-label">Input</span>
                          <code>{formatValue(testCase.input_data)}</code>
                        </div>
                        <div>
                          <span className="test-case-label">Expected output</span>
                          <code>{formatValue(testCase.expected_output)}</code>
                        </div>
                      </div>
                    ))}
                  </div>
                </details>
              ))}
            </div>
          )}
        </section>
      </div>
    </>
  );
}

function formatValue(value: unknown): string {
  return JSON.stringify(value) ?? "undefined";
}
