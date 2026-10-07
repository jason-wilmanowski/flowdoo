import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router";
import { useStore } from "zustand";

import { useStores } from "@/app/appContext";
import { BottomBar } from "@/app/shell/BottomBar";
import type { Trace } from "@/datasource";
import { cursorOf, stepAt } from "@/lib/replay/cursor";
import type { TraceIndex } from "@/lib/replay/traceIndex";
import {
  Button,
  buttonClassName,
  EmptyState,
  Skeleton,
  SplitPanel,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/ui";

import { formFromCommand } from "../startTrace/command";
import { StartTraceDialog } from "../startTrace/StartTraceDialog";
import { ChangeTimeline } from "./ChangeTimeline";
import { buildCallTree, revealStep } from "./model/callTree";
import { ModelGraphView } from "./ModelGraphView";
import { ReplayBar } from "./ReplayBar";
import { StepDetailsPane } from "./StepDetailsPane";
import { StepTreePane } from "./StepTreePane";
import { TraceHeader } from "./TraceHeader";
import styles from "./TraceView.module.css";

function Workspace({ trace, index }: { trace: Trace; index: TraceIndex }) {
  const { replay } = useStores();
  const cursor = useStore(replay, (state) => state.cursor);
  const goTo = useStore(replay, (state) => state.goTo);
  const step = stepAt(index, cursor);
  const tree = useMemo(() => buildCallTree(index), [index]);
  // rows whose expansion differs from "relevant paths open"
  const [toggled, setToggled] = useState<ReadonlySet<string>>(() => new Set());

  /** Move the replay to a step; jumps from elsewhere also unfold the tree to it. */
  const select = useCallback(
    (id: string, reveal = false) => {
      const position = cursorOf(index, id);
      if (position === null) return;
      goTo(position);
      if (reveal) setToggled((current) => revealStep(tree, current, id));
    },
    [index, goTo, tree],
  );
  const jump = useCallback(
    (id: string) => {
      select(id, true);
    },
    [select],
  );

  const jumpToModel = (model: string) => {
    const from = cursor ?? 0;
    const later = index.ordered.find((s, i) => i > from && s.model === model);
    const target = later ?? index.ordered.find((s) => s.model === model);
    if (target) jump(target.id);
  };

  const odooError = trace.payload?.error;
  return (
    <>
      <div className={styles.split}>
        <SplitPanel
          id="trace"
          start={{
            label: "Calls",
            content: (
              <StepTreePane
                tree={tree}
                stepCount={index.ordered.length}
                toggled={toggled}
                onToggled={setToggled}
                selectedStepId={step?.id ?? null}
                onSelectStep={select}
              />
            ),
            defaultWidth: "var(--panel-left-w)",
            minWidth: 220,
            maxWidth: 640,
          }}
          end={{
            label: "Step details",
            content: <StepDetailsPane step={step} index={index} tree={tree} onSelect={jump} />,
            defaultWidth: "var(--panel-right-w)",
            minWidth: 300,
            maxWidth: 720,
          }}
        >
          <div className={styles.main}>
            {odooError ? (
              <div className={styles.odooError} role="alert">
                <strong>Odoo raised {odooError.type}:</strong> {odooError.message}. The steps up to
                the error are recorded; failed steps are marked in the tree.
              </div>
            ) : null}
            <Tabs defaultValue="graph" className={styles.mainTabs}>
              <TabsList aria-label="Views of the run">
                <TabsTrigger value="graph">Model graph</TabsTrigger>
                <TabsTrigger value="changes">Changes over time</TabsTrigger>
              </TabsList>
              <TabsContent value="graph" className={styles.graphTab}>
                <ModelGraphView
                  index={index}
                  activeModel={step?.model ?? null}
                  onModel={jumpToModel}
                />
              </TabsContent>
              <TabsContent value="changes" className={styles.scroll}>
                <ChangeTimeline index={index} position={cursor} onSelect={jump} />
              </TabsContent>
            </Tabs>
          </div>
        </SplitPanel>
      </div>
      <BottomBar label="Replay controls">
        <ReplayBar replay={replay} />
      </BottomBar>
    </>
  );
}

/** /traces/:traceId: replay of a recorded run. */
export function TraceViewPage() {
  const { traceId = "" } = useParams();
  const { currentTrace } = useStores();
  const trace = useStore(currentTrace, (state) => state.trace);
  const index = useStore(currentTrace, (state) => state.index);
  const phase = useStore(currentTrace, (state) => state.phase);
  const error = useStore(currentTrace, (state) => state.error);
  const load = useStore(currentTrace, (state) => state.load);
  const [runAgain, setRunAgain] = useState(false);

  useEffect(() => {
    if (currentTrace.getState().trace?.id !== traceId) void load(traceId);
  }, [currentTrace, load, traceId]);

  if (phase === "error" && error) {
    const missing = error.status === 404;
    return (
      <main className={styles.island}>
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
      </main>
    );
  }
  if (!trace || trace.id !== traceId) {
    return (
      <main className={styles.island}>
        <Skeleton rows={10} label="Loading trace" />
      </main>
    );
  }

  const entrypoint = trace.payload?.entrypoint;
  return (
    <div className={styles.page}>
      <div className={styles.headerIsland}>
        <TraceHeader
          trace={trace}
          onRunAgain={() => {
            setRunAgain(true);
          }}
        />
      </div>
      {trace.payload === null || !index ? (
        <main className={styles.island}>
          <EmptyState
            tone="danger"
            message={`The recording failed, so there are no steps: ${trace.error ?? "no reason given"}`}
            action={
              <Button
                variant="primary"
                onClick={() => {
                  setRunAgain(true);
                }}
              >
                Run again
              </Button>
            }
          />
        </main>
      ) : (
        <Workspace key={trace.id} trace={trace} index={index} />
      )}
      {runAgain ? (
        <StartTraceDialog
          open
          onOpenChange={setRunAgain}
          initial={formFromCommand({
            entrypoint_model: trace.entrypoint_model,
            entrypoint_method: trace.entrypoint_method,
            record_ids: entrypoint?.record_ids ?? [],
            kwargs: entrypoint?.kwargs ?? {},
            context: entrypoint?.context ?? {},
            dry_run: true,
          })}
        />
      ) : null}
    </div>
  );
}
