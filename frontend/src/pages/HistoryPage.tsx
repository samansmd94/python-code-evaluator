import { Clock3, FileSearch2 } from "lucide-react";
import { PageHeader } from "../components/PageHeader";

export function HistoryPage() {
  return (
    <>
      <PageHeader
        eyebrow="Your activity"
        title="Evaluation history"
        description="Review past evaluation runs and their detailed reports."
      />
      <section className="history-empty surface-card">
        <span className="history-empty-icon"><FileSearch2 size={23} /></span>
        <p className="eyebrow">History is not connected yet</p>
        <h2>No history list is available</h2>
        <p>
          The backend can retrieve an evaluation when its ID is known, but it
          does not yet provide a list of previous evaluations. This page will
          show saved runs when that endpoint is added.
        </p>
        <span className="history-capability"><Clock3 size={15} /> No activity is being fabricated</span>
      </section>
    </>
  );
}
