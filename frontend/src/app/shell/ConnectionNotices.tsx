import { CircleAlert, TriangleAlert } from "lucide-react";
import { useStore } from "zustand";

import { Icon } from "@/ui";

import { useStores } from "../appContext";
import styles from "./ConnectionNotices.module.css";

/** Problems and warnings from GET /odoo/status as plain text, exactly as the backend says. */
export function ConnectionNotices() {
  const { connection } = useStores();
  const status = useStore(connection, (state) => state.status);
  const error = useStore(connection, (state) => state.error);

  const problems = error ? [`The API did not answer: ${error.message}`] : (status?.problems ?? []);
  const warnings = error ? [] : (status?.warnings ?? []);
  if (problems.length === 0 && warnings.length === 0) return null;

  return (
    <section className={styles.notices} aria-label="Connection notices">
      <ul className={styles.list}>
        {problems.map((text) => (
          <li key={`p-${text}`} className={styles.problem}>
            <span className={styles.icon}>
              <Icon icon={CircleAlert} compact />
            </span>
            <strong className={styles.kind}>Problem</strong>
            <span>{text}</span>
          </li>
        ))}
        {warnings.map((text) => (
          <li key={`w-${text}`} className={styles.warning}>
            <span className={styles.icon}>
              <Icon icon={TriangleAlert} compact />
            </span>
            <strong className={styles.kind}>Warning</strong>
            <span>{text}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
