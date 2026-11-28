import { Settings2 } from "lucide-react";
import { PageHeader } from "../components/PageHeader";

export function SettingsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Workspace preferences"
        title="Settings"
        description="Configuration for the local evaluator workspace."
      />
      <section className="settings-placeholder surface-card">
        <span className="history-empty-icon"><Settings2 size={22} /></span>
        <h2>Settings are not available yet</h2>
        <p>
          This page is a placeholder. The backend URL can currently be changed
          with the frontend environment file; no in-app settings are being
          presented as active controls.
        </p>
        <code>VITE_API_BASE_URL</code>
      </section>
    </>
  );
}
