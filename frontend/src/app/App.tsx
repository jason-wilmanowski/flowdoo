import { lazy, Suspense } from "react";

import { Spinner } from "@/ui";

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
  return <main>Flowdoo</main>;
}
