import type { ReactNode } from "react";
import { AlertCircle, LoaderCircle, PackageOpen } from "lucide-react";

interface StatePanelProps {
  kind: "loading" | "error" | "empty";
  title: string;
  message: string;
  action?: ReactNode;
}

export function StatePanel({
  kind,
  title,
  message,
  action,
}: StatePanelProps) {
  const Icon =
    kind === "loading"
      ? LoaderCircle
      : kind === "error"
        ? AlertCircle
        : PackageOpen;

  return (
    <section
      className="state-panel"
      role={kind === "error" ? "alert" : "status"}
      aria-live="polite"
    >
      <span className={`state-icon state-icon-${kind}`}>
        <Icon size={19} className={kind === "loading" ? "animate-spin" : ""} />
      </span>
      <div>
        <h2>{title}</h2>
        <p>{message}</p>
        {action ? <div className="mt-4">{action}</div> : null}
      </div>
    </section>
  );
}
