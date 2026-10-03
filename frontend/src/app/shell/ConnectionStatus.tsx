import { RefreshCw } from "lucide-react";
import { useStore } from "zustand";

import { Badge, IconButton, Spinner } from "@/ui";

import { useStores } from "../appContext";
import styles from "./TopBar.module.css";

/** Short state of the Odoo connection; the details are in the notices below the top bar. */
export function ConnectionStatus() {
  const { connection } = useStores();
  const status = useStore(connection, (state) => state.status);
  const phase = useStore(connection, (state) => state.phase);
  const refresh = useStore(connection, (state) => state.refresh);

  let state;
  if (phase === "error") state = <Badge tone="danger">API unreachable</Badge>;
  else if (!status) state = <Spinner label="Checking connection" compact />;
  else if (status.ok) state = <Badge tone="success">Odoo connected</Badge>;
  else state = <Badge tone="danger">Odoo not ready</Badge>;

  return (
    <div className={styles.group}>
      {state}
      {status?.database ? <span className={styles.mono}>{status.database}</span> : null}
      <IconButton
        icon={RefreshCw}
        label="Check connection again"
        compact
        disabled={phase === "loading"}
        onClick={() => {
          void refresh();
        }}
      />
    </div>
  );
}
