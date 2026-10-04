import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router";

import { TraceListPage } from "@/features/traceList/TraceListPage";
import { Skeleton } from "@/ui";

import { NotFoundPage } from "./pages/NotFoundPage";
import { OverviewPage } from "./pages/OverviewPage";
import { AppShell } from "./shell/AppShell";

// The trace view brings React Flow; load it when a trace is opened.
const TraceViewPage = lazy(() =>
  import("@/features/traceView/TraceViewPage").then((m) => ({ default: m.TraceViewPage })),
);

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/traces" replace />} />
        <Route path="traces" element={<TraceListPage />} />
        <Route
          path="traces/:traceId"
          element={
            <Suspense fallback={<Skeleton rows={10} label="Loading trace" />}>
              <TraceViewPage />
            </Suspense>
          }
        />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
