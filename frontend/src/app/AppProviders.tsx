import { useEffect, useMemo, useState, type ReactNode } from "react";

import { createDataSource, type DataSource, type DataSourceKind } from "@/datasource";
import { createAppStores } from "@/stores";
import { TooltipProvider } from "@/ui";

import { AppContext, type AppContextValue } from "./appContext";
import { ShortcutProvider } from "./shortcuts/ShortcutProvider";

export interface AppProvidersProps {
  initialDataSource: DataSourceKind;
  /** Injected so tests can run on fixtures without delay. */
  createSource?: (kind: DataSourceKind) => DataSource;
  /** Called after a switch, e.g. to remember the choice. */
  onDataSourceChange?: (kind: DataSourceKind) => void;
  children: ReactNode;
}

/** Stores for the active data source, tooltips and keyboard shortcuts for the whole app. */
export function AppProviders({
  initialDataSource,
  createSource = createDataSource,
  onDataSourceChange,
  children,
}: AppProvidersProps) {
  const [dataSource, setDataSource] = useState(initialDataSource);
  const stores = useMemo(
    () => createAppStores(createSource(dataSource)),
    [createSource, dataSource],
  );

  useEffect(() => {
    void stores.connection.getState().refresh();
  }, [stores]);

  const value = useMemo<AppContextValue>(
    () => ({
      stores,
      dataSource,
      switchDataSource: (kind) => {
        setDataSource(kind);
        onDataSourceChange?.(kind);
      },
    }),
    [stores, dataSource, onDataSourceChange],
  );

  return (
    <AppContext.Provider value={value}>
      <TooltipProvider>
        <ShortcutProvider>{children}</ShortcutProvider>
      </TooltipProvider>
    </AppContext.Provider>
  );
}
