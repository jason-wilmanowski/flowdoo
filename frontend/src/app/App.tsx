import { lazy, Suspense } from "react";
import { BrowserRouter } from "react-router";

import { Spinner } from "@/ui";

import { AppProviders } from "./AppProviders";
import { AppRoutes } from "./AppRoutes";
import { initialDataSourceKind, storeDataSourceKind } from "./dataSourceChoice";

// Development-only UI kit; the import is dropped from production builds.
const KitGallery = import.meta.env.DEV
  ? lazy(() => import("@/app/kit/KitGallery").then((m) => ({ default: m.KitGallery })))
  : null;

export function App() {
  if (KitGallery && window.location.pathname === "/_kit") {
    return (
      <Suspense fallback={<Spinner label="Loading UI kit" />}>
        <KitGallery />
      </Suspense>
    );
  }
  return (
    <BrowserRouter>
      <AppProviders
        initialDataSource={initialDataSourceKind()}
        onDataSourceChange={storeDataSourceKind}
      >
        <AppRoutes />
      </AppProviders>
    </BrowserRouter>
  );
}
