import { useEffect } from "react";
import { Link, useParams } from "react-router";
import { useStore } from "zustand";

import type { Trace } from "@/datasource";
import {
  Badge,
  Button,
  buttonClassName,
  EmptyState,
  Skeleton,
  SplitPanel,
  type BadgeTone,
} from "@/ui";

import { useStores } from "../appContext";
import { BottomBar } from "../shell/BottomBar";
import styles from "./Page.module.css";

const STATUS_TONES: Record<Trace["status"], BadgeTone> = {
  pending: "neutral",
  running: "accent",
  succeeded: "success",
  failed: "danger",
};

function Pane({ title, children }: { title: string; children: string }) {
  return (
    <div className={styles.pane}>
      <h2 className={styles.paneTitle}>{title}</h2>
      <p>{children}</p>
    </div>
  );
}

function TraceWorkspace({ trace, stepCount }: { trace: Trace; stepCount: number }) {
  const odooError = trace.payload?.error;
  return (
    <div className={styles.workspace}>
      <div className={styles.split}>
        <SplitPanel
          id="trace"
          start={{
            label: "Steps",
            content: (
              <Pane title="Steps">{`${String(stepCount)} steps recorded. The step tree is not built yet.`}</Pane>
            ),
            defaultWidth: "var(--panel-left-w)",
            minWidth: 200,
            maxWidth: 520,
          }}
          end={{
            label: "Step details",
            content: (
              <Pane title="Step details">
                Field changes, module and MRO position of the selected step will show here. Not
                built yet.
              </Pane>
            ),
            defaultWidth: "var(--panel-right-w)",
            minWidth: 280,
            maxWidth: 640,
          }}
        >
          <div className={styles.section}>
            <h1 className={styles.heading}>
              <span className={styles.mono}>
                {trace.entrypoint_model}.{trace.entrypoint_method}
              </span>
              <Badge tone={STATUS_TONES[trace.status]}>{trace.status}</Badge>
              <Badge tone={trace.dry_run ? "neutral" : "danger"}>
                {trace.dry_run ? "dry run" : "not a dry run"}
              </Badge>
            </h1>
            {trace.payload === null ? (
              <EmptyState
                tone="danger"
                message={`The recording failed, so there are no steps: ${trace.error ?? "no reason given"}`}
              />
            ) : (
              <>
                {odooError ? (
                  <EmptyState
                    tone="danger"
                    message={`Odoo raised ${odooError.type}: ${odooError.message}`}
                  />
                ) : null}
                <p className={styles.muted}>The graph and timeline of the run are not built yet.</p>
              </>
            )}
          </div>
        </SplitPanel>
      </div>
      <BottomBar label="Replay controls">Replay controls are not built yet.</BottomBar>
    </div>
  );
}

/** Frame of the trace view: three panels and the bottom bar with placeholder content. */
export function TracePage() {
  const { traceId = "" } = useParams();
  const { currentTrace } = useStores();
  const trace = useStore(currentTrace, (state) => state.trace);
  const stepCount = useStore(currentTrace, (state) => state.index?.ordered.length ?? 0);
  const phase = useStore(currentTrace, (state) => state.phase);
  const error = useStore(currentTrace, (state) => state.error);
  const load = useStore(currentTrace, (state) => state.load);

  useEffect(() => {
    void load(traceId);
  }, [load, traceId]);

  if (phase === "error" && error) {
    const missing = error.status === 404;
    return (
      <main className={styles.page}>
        <div className={styles.section}>
          <EmptyState
            tone="danger"
            message={
              missing
                ? `There is no trace with the id ${traceId}.`
                : `Could not load the trace: ${error.message}`
            }
            action={
              missing ? (
                <Link to="/traces" className={buttonClassName("primary")}>
                  Back to traces
                </Link>
              ) : (
                <Button
                  onClick={() => {
                    void load(traceId);
                  }}
                >
                  Retry
                </Button>
              )
            }
          />
        </div>
      </main>
    );
  }
  if (phase !== "ready" || !trace || trace.id !== traceId) {
    return (
      <main className={styles.page}>
        <div className={styles.section}>
          <Skeleton rows={8} label="Loading trace" />
        </div>
      </main>
    );
  }
  return <TraceWorkspace trace={trace} stepCount={stepCount} />;
}
