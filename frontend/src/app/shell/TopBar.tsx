import { Keyboard, Moon, Sun } from "lucide-react";
import { NavLink } from "react-router";

import { Badge, Button, IconButton } from "@/ui";

import { useDataSourceSwitch } from "../appContext";
import { useOpenShortcutHelp } from "../shortcuts/shortcutContext";
import { ConnectionStatus } from "./ConnectionStatus";
import styles from "./TopBar.module.css";
import { useTheme } from "./useTheme";

const SOURCE_NAMES = { api: "API", fixtures: "Fixtures" } as const;

function navClass({ isActive }: { isActive: boolean }) {
  return [styles.navLink, isActive ? styles.navActive : ""].join(" ").trim();
}

export function TopBar() {
  const { dataSource, switchDataSource } = useDataSourceSwitch();
  const [theme, setTheme] = useTheme();
  const openHelp = useOpenShortcutHelp();
  const otherSource = dataSource === "api" ? "fixtures" : "api";

  return (
    <header className={styles.topBar}>
      <span className={styles.product}>Flowdoo</span>
      <nav aria-label="Main" className={styles.nav}>
        <NavLink to="/traces" className={navClass}>
          Traces
        </NavLink>
        <NavLink to="/overview" className={navClass}>
          Overview
        </NavLink>
      </nav>

      <div className={styles.end}>
        <Badge title="Every run is rolled back in Odoo; nothing is written.">Dry run</Badge>
        <ConnectionStatus />
        <div className={styles.group}>
          <span className={styles.label}>Data</span>
          <Badge mono>{SOURCE_NAMES[dataSource]}</Badge>
          <Button
            variant="ghost"
            compact
            onClick={() => {
              switchDataSource(otherSource);
            }}
          >
            Use {SOURCE_NAMES[otherSource]}
          </Button>
        </div>
        <IconButton
          icon={theme === "dark" ? Sun : Moon}
          label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          onClick={() => {
            setTheme(theme === "dark" ? "light" : "dark");
          }}
        />
        <IconButton icon={Keyboard} label="Keyboard shortcuts (?)" onClick={openHelp} />
      </div>
    </header>
  );
}
