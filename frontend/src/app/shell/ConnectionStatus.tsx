import { useStore } from "zustand";

import { useStores } from "../appContext";
import styles from "./TopBar.module.css";

type Tone = "ok" | "problem" | "pending";

/** Read-only state of the Odoo connection; details and "check again" are in the settings. */
export function ConnectionStatus() {
  const { connection } = useStores();
  const status = useStore(connection, (state) => state.status);
  const phase = useStore(connection, (state) => state.phase);

  let tone: Tone = "pending";
  let text = "Checking connection";
  if (phase === "error") {
    tone = "problem";
    text = "API unreachable";
  } else if (status?.ok) {
    tone = "ok";
    text = "Odoo connected";
  } else if (status) {
    tone = "problem";
    text = "Odoo not ready";
  }

  return (
    <span className={styles.status} role="status">
      <span className={[styles.dot, styles[tone]].join(" ")} aria-hidden="true" />
      <span>{text}</span>
      {status?.database ? <span className={styles.statusDetail}>{status.database}</span> : null}
    </span>
  );
}
