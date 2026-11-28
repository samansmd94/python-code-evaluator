import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./layout/AppShell";
import { DashboardPage } from "./pages/DashboardPage";
import { ExerciseDetailPage } from "./pages/ExerciseDetailPage";
import { ExercisesPage } from "./pages/ExercisesPage";
import { HistoryPage } from "./pages/HistoryPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { SettingsPage } from "./pages/SettingsPage";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="exercises" element={<ExercisesPage />} />
        <Route path="exercises/:slug" element={<ExerciseDetailPage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="404" element={<NotFoundPage />} />
        <Route path="*" element={<Navigate to="/404" replace />} />
      </Route>
    </Routes>
  );
}
