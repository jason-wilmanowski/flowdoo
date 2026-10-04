import { Navigate, Route, Routes } from "react-router";

import { TraceListPage } from "@/features/traceList/TraceListPage";

import { NotFoundPage } from "./pages/NotFoundPage";
import { OverviewPage } from "./pages/OverviewPage";
import { TracePage } from "./pages/TracePage";
import { AppShell } from "./shell/AppShell";

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/traces" replace />} />
        <Route path="traces" element={<TraceListPage />} />
        <Route path="traces/:traceId" element={<TracePage />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
