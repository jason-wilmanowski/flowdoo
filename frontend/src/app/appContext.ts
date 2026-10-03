import { createContext, useContext } from "react";

import type { DataSourceKind } from "@/datasource";
import type { AppStores } from "@/stores";

export interface AppContextValue {
  stores: AppStores;
  dataSource: DataSourceKind;
  switchDataSource: (kind: DataSourceKind) => void;
}

export const AppContext = createContext<AppContextValue | null>(null);

function useAppContext(): AppContextValue {
  const context = useContext(AppContext);
  if (!context) throw new Error("App state is used outside of <AppProviders>");
  return context;
}

/** The stores of the active data source; read them with zustand's `useStore`. */
export function useStores(): AppStores {
  return useAppContext().stores;
}

export function useDataSourceSwitch(): Pick<AppContextValue, "dataSource" | "switchDataSource"> {
  const { dataSource, switchDataSource } = useAppContext();
  return { dataSource, switchDataSource };
}
