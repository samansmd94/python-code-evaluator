import { useState } from "react";
import {
  Activity,
  BookOpenCheck,
  ChevronRight,
  Code2,
  LayoutDashboard,
  Menu,
  Settings2,
  X,
} from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

const navigation = [
  { label: "Dashboard", to: "/", icon: LayoutDashboard, end: true },
  { label: "Exercises", to: "/exercises", icon: BookOpenCheck },
  { label: "Evaluation History", to: "/history", icon: Activity },
  { label: "Settings", to: "/settings", icon: Settings2 },
];

function currentSection(pathname: string): string {
  if (pathname.startsWith("/exercises")) return "Exercises";
  if (pathname.startsWith("/history")) return "Evaluation History";
  if (pathname.startsWith("/settings")) return "Settings";
  return "Dashboard";
}

export function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const section = currentSection(location.pathname);

  return (
    <div className="app-frame">
      {menuOpen ? (
        <button
          className="mobile-scrim"
          aria-label="Close navigation"
          onClick={() => setMenuOpen(false)}
        />
      ) : null}
      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">
            <Code2 size={19} strokeWidth={2.5} />
          </div>
          <div>
            <p className="brand-title">Code Evaluator</p>
            <p className="brand-caption">Python workspace</p>
          </div>
          <button
            className="sidebar-close"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
          >
            <X size={19} />
          </button>
        </div>

        <div className="nav-section-label">Workspace</div>
        <nav className="side-nav" aria-label="Main navigation">
          {navigation.map(({ label, to, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) =>
                `nav-link ${isActive ? "nav-link-active" : ""}`
              }
            >
              <Icon size={18} strokeWidth={1.9} />
              <span>{label}</span>
              <ChevronRight className="nav-chevron" size={15} />
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-status-dot" />
          <div>
            <p className="sidebar-status-title">Catalog connected</p>
            <p className="sidebar-status-caption">Local API workspace</p>
          </div>
        </div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <button
            className="mobile-menu-button"
            aria-label="Open navigation"
            onClick={() => setMenuOpen(true)}
          >
            <Menu size={20} />
          </button>
          <div className="breadcrumbs" aria-label="Breadcrumb">
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>{section}</strong>
          </div>
          <div className="topbar-meta">
            <span className="api-indicator" />
            <span>Python evaluator</span>
          </div>
        </header>
        <main className="page-content" key={location.pathname}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
