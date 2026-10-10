import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router";

import { TraceListPage } from "@/features/traceList/TraceListPage";
import { Skeleton } from "@/ui";

import { NotFoundPage } from "./pages/NotFoundPage";
import { AppShell } from "./shell/AppShell";

// The trace view and the overview bring React Flow; load them when they are opened.
const OverviewPage = lazy(() =>
  import("@/features/overview/OverviewPage").then((m) => ({ default: m.OverviewPage })),
);
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
        <Route
          path="overview/:model?"
          element={
            <Suspense fallback={<Skeleton rows={10} label="Loading overview" />}>
              <OverviewPage />
            </Suspense>
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
