import type { Step } from "@/generated/trace";
import { formatDuration } from "@/lib/format";
import type { TraceIndex } from "@/lib/replay/traceIndex";
import {
  Badge,
  CodeValue,
  DiffRow,
  Icon,
  StepRow,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/ui";

import { stepKind } from "../traces/stepKinds";
import { changesByRecord } from "./model/changes";
import { ancestorsOf } from "./model/treeRows";
import { formatValue } from "./model/values";
import styles from "./TraceView.module.css";

const NOT_DETERMINED = "not determined";

function yesNo(value: boolean | null): string {
  if (value === null) return NOT_DETERMINED;
  return value ? "yes" : "no";
}

function Changes({ step }: { step: Step }) {
  if (step.changes.length === 0) {
    return <p className={styles.hint}>This step changed no field values.</p>;
  }
  return (
    <div className={styles.changeGroups}>
      {changesByRecord(step).map((group) => (
        <section
          key={`${group.model}-${String(group.recordId)}`}
          aria-label={`${group.model} ${String(group.recordId)}`}
        >
          <h3 className={styles.recordTitle}>
            {group.model} <span className={styles.muted}>#{group.recordId}</span>
          </h3>
          {group.changes.map((change) => (
            <DiffRow
              key={change.field}
              field={change.field}
              oldValue={formatValue(change.old)}
              newValue={formatValue(change.new)}
            />
          ))}
        </section>
      ))}
    </div>
  );
}

function Call({ step }: { step: Step }) {
  const kind = stepKind(step.kind);
  const facts: [string, React.ReactNode][] = [
    [
      "Kind",
      <span key="k" className={styles.kindFact}>
        <Icon icon={kind.icon} compact />
        {kind.label}
      </span>,
    ],
    ["Model", <code key="m">{step.model}</code>],
    ["Method", <code key="me">{step.method}</code>],
    [
      "Module",
      <Badge key="mo" mono>
        {step.module ?? NOT_DETERMINED}
      </Badge>,
    ],
    [
      "MRO position",
      <span key="p">
        {step.mro_position === null ? NOT_DETERMINED : <code>{step.mro_position}</code>}
        {step.mro_position === 0 ? <span className={styles.muted}> (most derived)</span> : null}
      </span>,
    ],
    ["Calls super()", yesNo(step.calls_super)],
    [
      "Records",
      <code key="r">{step.record_ids.length > 0 ? step.record_ids.join(", ") : "none"}</code>,
    ],
    ["Duration", <code key="d">{formatDuration(step.duration_ms)}</code>],
  ];
  return (
    <div className={styles.callTab}>
      <dl className={styles.facts}>
        {facts.map(([term, value]) => (
          <div key={term} className={styles.fact}>
            <dt>{term}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <div className={styles.summaryBlock}>
        <h3 className={styles.recordTitle}>Arguments</h3>
        {step.args_summary ? (
          <CodeValue value={step.args_summary} label="arguments" />
        ) : (
          <p className={styles.hint}>None recorded.</p>
        )}
      </div>
      <div className={styles.summaryBlock}>
        <h3 className={styles.recordTitle}>Returned</h3>
        {step.return_summary ? (
          <CodeValue value={step.return_summary} label="return value" />
        ) : (
          <p className={styles.hint}>None recorded.</p>
        )}
      </div>
      {step.error ? (
        <div className={styles.stepError} role="alert">
          <strong>{step.error.type}</strong>: {step.error.message}
        </div>
      ) : null}
    </div>
  );
}

function Path({
  step,
  index,
  onSelect,
}: {
  step: Step;
  index: TraceIndex;
  onSelect: (id: string) => void;
}) {
  const path = [...ancestorsOf(index, step.id).reverse(), step.id];
  return (
    <ol className={styles.path} aria-label="Call path">
      {path.map((id) => {
        const item = index.byId.get(id);
        if (!item) return null;
        const kind = stepKind(item.kind);
        return (
          <li key={id}>
            <button
              type="button"
              className={[styles.pathItem, id === step.id ? styles.pathCurrent : ""]
                .join(" ")
                .trim()}
              aria-current={id === step.id ? "step" : undefined}
              onClick={() => {
                onSelect(id);
              }}
            >
              <StepRow
                kindIcon={kind.icon}
                kindLabel={kind.label}
                kindTone={kind.tone}
                model={item.model}
                method={item.method}
                module={item.module}
                duration={formatDuration(item.duration_ms)}
                changes={item.changes.length}
                failed={item.error !== null}
              />
            </button>
          </li>
        );
      })}
    </ol>
  );
}

export interface StepDetailsPaneProps {
  step: Step | null;
  index: TraceIndex;
  onSelect: (id: string) => void;
}

/** Everything about the selected step: field changes, the implementation, the call path. */
export function StepDetailsPane({ step, index, onSelect }: StepDetailsPaneProps) {
  if (!step) {
    return <p className={styles.hint}>This trace has no steps.</p>;
  }
  return (
    <div className={styles.pane}>
      <div className={styles.paneHeader}>
        <h2 className={styles.detailTitle}>
          {step.model}.{step.method}
        </h2>
      </div>
      <Tabs defaultValue="changes" className={styles.detailTabs}>
        <TabsList aria-label="Step details">
          <TabsTrigger value="changes">Changes ({step.changes.length})</TabsTrigger>
          <TabsTrigger value="call">Call</TabsTrigger>
          <TabsTrigger value="path">Path</TabsTrigger>
        </TabsList>
        <div className={styles.scroll}>
          <TabsContent value="changes">
            <Changes step={step} />
          </TabsContent>
          <TabsContent value="call">
            <Call step={step} />
          </TabsContent>
          <TabsContent value="path">
            <Path step={step} index={index} onSelect={onSelect} />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
