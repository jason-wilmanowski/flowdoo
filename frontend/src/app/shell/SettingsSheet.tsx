import { CircleCheck, CircleX, RefreshCw } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useStore } from "zustand";

import { groupShortcuts } from "@/lib/shortcuts/registry";
import { Button, Dialog, Icon, Kbd, SegmentedControl } from "@/ui";

import { useDataSourceSwitch, useStores } from "../appContext";
import { useRegisteredShortcuts } from "../shortcuts/shortcutContext";
import styles from "./SettingsSheet.module.css";
import { useThemeChoice } from "./useTheme";

const THEMES = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "System" },
] as const;

const SOURCES = [
  { value: "api", label: "API" },
  { value: "fixtures", label: "Fixtures" },
] as const;

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className={styles.section} aria-label={title}>
      <h3 className={styles.sectionTitle}>{title}</h3>
      {children}
    </section>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className={styles.row}>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

const yesNo = (value: boolean) => (value ? "yes" : "no");

type CheckOutcome = "ok" | "failed";

/** How long a check result stays, and how long it takes to fade (the motion duration). */
const RESULT_SHOWN_MS = 3000;
const RESULT_LEAVING_MS = 120;

interface ShownResult {
  outcome: CheckOutcome;
  leaving: boolean;
}

/** The answer to an explicit "Check again": slides out of the button, settles, fades. */
function CheckResult({ outcome, leaving }: ShownResult) {
  const ok = outcome === "ok";
  return (
    <span
      className={[
        styles.checkResult,
        ok ? styles.checkOk : styles.checkFailed,
        leaving ? styles.checkLeaving : "",
      ]
        .join(" ")
        .trim()}
    >
      <Icon icon={ok ? CircleCheck : CircleX} compact />
      {ok ? "Connection works" : "Connection has problems"}
    </span>
  );
}

/**
 * The result of the last check the user asked for. It shows for a few seconds, then fades
 * and goes. Timers rather than animation events, so it also goes with reduced motion.
 */
function useCheckResult(): [ShownResult | null, (outcome: CheckOutcome | null) => void] {
  const [shown, setShown] = useState<ShownResult | null>(null);

  useEffect(() => {
    if (shown === null) return;
    const timer = window.setTimeout(
      () => {
        setShown(shown.leaving ? null : { ...shown, leaving: true });
      },
      shown.leaving ? RESULT_LEAVING_MS : RESULT_SHOWN_MS,
    );
    return () => {
      window.clearTimeout(timer);
    };
  }, [shown]);

  const show = (outcome: CheckOutcome | null) => {
    setShown(outcome === null ? null : { outcome, leaving: false });
  };
  return [shown, show];
}

function Connection() {
  const { connection } = useStores();
  const status = useStore(connection, (state) => state.status);
  const phase = useStore(connection, (state) => state.phase);
  const error = useStore(connection, (state) => state.error);
  const refresh = useStore(connection, (state) => state.refresh);
  // only the result of a check the user asked for; a new check clears it until it is done
  const [result, showResult] = useCheckResult();

  const checkAgain = async () => {
    showResult(null);
    await refresh();
    const { phase: done, status: checked } = connection.getState();
    showResult(done === "ready" && checked?.ok ? "ok" : "failed");
  };

  return (
    <Section title="Connection">
      {error ? (
        <p className={styles.problem}>The API did not answer: {error.message}</p>
      ) : status ? (
        <dl className={styles.facts}>
          <Row label="Odoo">
            <code>{status.url ?? "not configured"}</code>
          </Row>
          <Row label="Database">
            <code>{status.database ?? "—"}</code>
          </Row>
          <Row label="Version">
            <code>{status.server_version ?? "—"}</code>
          </Row>
          <Row label="User">
            <code>{status.user_login ?? "—"}</code>
          </Row>
          <Row label="Addon">
            {status.addon_installed ? (status.addon_state ?? "installed") : "missing"}
          </Row>
          <Row label="Tracing">{yesNo(status.tracing_enabled && status.recorder_available)}</Row>
          <Row label="Neutralised">
            {status.database_neutralized === null || status.database_neutralized === undefined
              ? "unknown"
              : yesNo(status.database_neutralized)}
          </Row>
        </dl>
      ) : (
        <p className={styles.hint}>Checking…</p>
      )}
      <div className={styles.check}>
        <Button
          compact
          icon={RefreshCw}
          loading={phase === "loading"}
          onClick={() => {
            void checkAgain();
          }}
        >
          Check again
        </Button>
        <span role="status" className={styles.checkStatus}>
          {result ? <CheckResult {...result} /> : null}
        </span>
      </div>
    </Section>
  );
}

function Shortcuts() {
  const shortcuts = useRegisteredShortcuts();
  return (
    <Section title="Keyboard shortcuts">
      {groupShortcuts(shortcuts).map(([group, items]) => (
        <div key={group} className={styles.shortcutGroup}>
          <h4 className={styles.groupTitle}>{group}</h4>
          <dl className={styles.shortcuts}>
            {items.map((shortcut) => (
              <div key={shortcut.id} className={styles.shortcut}>
                <dt>{shortcut.description}</dt>
                <dd>
                  <Kbd>{shortcut.label}</Kbd>
                </dd>
              </div>
            ))}
          </dl>
        </div>
      ))}
      <p className={styles.hint}>Shortcuts do not apply while typing in a field.</p>
    </Section>
  );
}

export interface SettingsSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** Preferences and connection details, in a panel from the right. */
export function SettingsSheet({ open, onOpenChange }: SettingsSheetProps) {
  const [theme, setTheme] = useThemeChoice();
  const { dataSource, switchDataSource } = useDataSourceSwitch();

  return (
    <Dialog open={open} onOpenChange={onOpenChange} title="Settings" variant="sheet">
      <div className={styles.sheet}>
        <Section title="Appearance">
          <SegmentedControl label="Theme" options={THEMES} value={theme} onChange={setTheme} />
        </Section>
        <Section title="Data source">
          <SegmentedControl
            label="Data source"
            options={SOURCES}
            value={dataSource}
            onChange={switchDataSource}
          />
          <p className={styles.hint}>
            {dataSource === "api"
              ? "Traces come from the Flowdoo API and your Odoo."
              : "Traces come from shared/fixtures; no backend or Odoo is used."}
          </p>
        </Section>
        <Connection />
        <Shortcuts />
      </div>
    </Dialog>
  );
}
