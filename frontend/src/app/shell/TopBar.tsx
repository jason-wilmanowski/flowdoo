import { Settings, Workflow } from "lucide-react";
import { useState } from "react";
import { NavLink } from "react-router";

import { Icon, IconButton } from "@/ui";

import { useDataSourceSwitch } from "../appContext";
import { useShortcut } from "../shortcuts/shortcutContext";
import { ConnectionStatus } from "./ConnectionStatus";
import { SettingsSheet } from "./SettingsSheet";
import styles from "./TopBar.module.css";

function navClass({ isActive }: { isActive: boolean }) {
  return [styles.navLink, isActive ? styles.navActive : ""].join(" ").trim();
}

/**
 * Left: product and navigation. Right: what is true right now (read-only status), then
 * the one action of the bar (settings), separated by a line.
 */
export function TopBar() {
  const { dataSource } = useDataSourceSwitch();
  const [settingsOpen, setSettingsOpen] = useState(false);
  useShortcut(
    { id: "settings", key: ",", label: ",", description: "Open settings", group: "General" },
    () => {
      setSettingsOpen((open) => !open);
    },
  );

  return (
    <header className={styles.topBar}>
      <span className={styles.product}>
        <span className={styles.mark} aria-hidden="true">
          <Icon icon={Workflow} compact />
        </span>
        Flowdoo
      </span>
      <nav aria-label="Main" className={styles.nav}>
        <NavLink to="/traces" className={navClass}>
          Traces
        </NavLink>
        <NavLink to="/overview" className={navClass}>
          Overview
        </NavLink>
      </nav>

      <div className={styles.end}>
        <div className={styles.statusArea} aria-label="Status">
          {dataSource === "fixtures" ? (
            <span className={styles.status}>
              <span className={[styles.dot, styles.pending].join(" ")} aria-hidden="true" />
              Fixture data
            </span>
          ) : (
            <ConnectionStatus />
          )}
          <span
            className={styles.status}
            title="Every run is rolled back in Odoo; nothing is written."
          >
            Dry run
          </span>
        </div>
        <span className={styles.divider} aria-hidden="true" />
        <IconButton
          icon={Settings}
          label="Settings (,)"
          className={styles.barButton}
          aria-expanded={settingsOpen}
          onClick={() => {
            setSettingsOpen(true);
          }}
        />
      </div>
      <SettingsSheet open={settingsOpen} onOpenChange={setSettingsOpen} />
    </header>
  );
}
