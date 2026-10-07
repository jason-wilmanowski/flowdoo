import { ChevronRight } from "lucide-react";
import { useMemo, type ReactNode } from "react";

import type { Step } from "@/generated/trace";
import { formatDuration } from "@/lib/format";
import type { TraceIndex } from "@/lib/replay/traceIndex";
import { Badge, CodeValue, DiffRow, Icon, StepRow } from "@/ui";

import { stepKind } from "../traces/stepKinds";
import { netChanges, type RecordEffect } from "./model/changes";
import { ancestorsOf } from "./model/treeRows";
import { formatValue } from "./model/values";
import styles from "./StepDetails.module.css";

const NOT_DETERMINED = "not determined";

function superText(value: boolean | null): string {
  if (value === null) return NOT_DETERMINED;
  return value ? "calls super()" : "no super()";
}

/** A collapsible part of the panel (native details: Enter/Space toggle it). */
function Section({
  title,
  count,
  hint,
  defaultOpen = true,
  children,
}: {
  title: string;
  count?: number;
  hint?: string;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  return (
    <details className={styles.section} open={defaultOpen}>
      <summary className={styles.summary}>
        <span className={styles.chevron}>
          <Icon icon={ChevronRight} compact />
        </span>
        <span className={styles.sectionTitle}>{title}</span>
        {count !== undefined ? <span className={styles.count}>{count}</span> : null}
        {hint ? <span className={styles.sectionHint}>{hint}</span> : null}
      </summary>
      <div className={styles.sectionBody}>{children}</div>
    </details>
  );
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className={styles.fact}>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function Changes({
  effects,
  onJump,
}: {
  effects: RecordEffect[];
  onJump: (stepId: string) => void;
}) {
  if (effects.length === 0) {
    return <p className={styles.hint}>No field changed in this call or in the calls it made.</p>;
  }
  return (
    <div className={styles.records}>
      {effects.map((record) => (
        <section
          key={`${record.model}-${String(record.recordId)}`}
          className={styles.record}
          aria-label={`${record.model} ${String(record.recordId)}`}
        >
          <h4 className={styles.recordTitle}>
            <code>{record.model}</code>
            <span className={styles.recordId}>#{record.recordId}</span>
            {record.created ? <Badge tone="success">created</Badge> : null}
          </h4>
          {record.fields.map((effect) => (
            <div key={effect.field} className={styles.effect}>
              <DiffRow
                field={effect.field}
                oldValue={formatValue(effect.old)}
                newValue={formatValue(effect.new)}
              />
              <button
                type="button"
                className={styles.jump}
                onClick={() => {
                  onJump(effect.lastStepId);
                }}
              >
                {effect.writes > 1 ? `${String(effect.writes)} writes, last in ` : "written in "}
                step {effect.lastPosition + 1}
              </button>
            </div>
          ))}
        </section>
      ))}
    </div>
  );
}

function CallPath({
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

/**
 * Everything about the selected step in one column: who implements it, what the call
 * changed (including the calls it made), its arguments, and how it was reached.
 */
export function StepDetailsPane({ step, index, onSelect }: StepDetailsPaneProps) {
  const effects = useMemo(() => (step ? netChanges(index, step.id) : []), [index, step]);
  if (!step) {
    return <p className={styles.hint}>This trace has no steps.</p>;
  }
  const kind = stepKind(step.kind);
  const fieldCount = effects.reduce((sum, record) => sum + record.fields.length, 0);
  const depth = ancestorsOf(index, step.id).length;

  return (
    <div className={styles.panel}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <span className={[styles.kind, kind.tone ? styles[kind.tone] : ""].join(" ").trim()}>
            <Icon icon={kind.icon} compact label={kind.label} />
          </span>
          <h2 className={styles.title}>
            {step.model}.{step.method}
          </h2>
        </div>
        <dl className={styles.facts}>
          <Fact label="Module">
            <code>{step.module ?? NOT_DETERMINED}</code>
          </Fact>
          <Fact label="MRO">
            {step.mro_position === null ? (
              NOT_DETERMINED
            ) : (
              <code>
                {step.mro_position}
                {step.mro_position === 0 ? " (most derived)" : ""}
              </code>
            )}
          </Fact>
          <Fact label="Super">{superText(step.calls_super)}</Fact>
          <Fact label="Records">
            <code>{step.record_ids.length > 0 ? step.record_ids.join(", ") : "none"}</code>
          </Fact>
          <Fact label="Duration">{formatDuration(step.duration_ms)}</Fact>
          <Fact label="Kind">{kind.label}</Fact>
        </dl>
        {step.error ? (
          <div className={styles.error} role="alert">
            <strong>{step.error.type}</strong>: {step.error.message}
          </div>
        ) : null}
      </header>

      <div className={styles.scroll}>
        <Section title="Changes" count={fieldCount} hint="this call and the calls it made">
          <Changes effects={effects} onJump={onSelect} />
        </Section>
        <Section title="Arguments and result">
          <div className={styles.values}>
            <span className={styles.valueLabel}>Arguments</span>
            {step.args_summary ? (
              <CodeValue value={step.args_summary} label="arguments" />
            ) : (
              <span className={styles.hint}>None recorded.</span>
            )}
            <span className={styles.valueLabel}>Returned</span>
            {step.return_summary ? (
              <CodeValue value={step.return_summary} label="return value" />
            ) : (
              <span className={styles.hint}>None recorded.</span>
            )}
          </div>
        </Section>
        <Section title="Call path" count={depth + 1} defaultOpen={false}>
          <CallPath step={step} index={index} onSelect={onSelect} />
        </Section>
      </div>
    </div>
  );
}
