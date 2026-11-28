import { Link } from "react-router-dom";
import { StatePanel } from "../components/StatePanel";

export function NotFoundPage() {
  return (
    <StatePanel
      kind="empty"
      title="Page not found"
      message="The page you requested is not part of this workspace."
      action={<Link to="/" className="button-secondary">Go to dashboard</Link>}
    />
  );
}
