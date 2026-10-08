import { ChevronRight } from "lucide-react";
import { useMemo, type ReactNode } from "react";

import type { Step } from "@/generated/trace";
import { formatDuration } from "@/lib/format";
import type { TraceIndex } from "@/lib/replay/traceIndex";
import { Badge, CodeValue, DiffRow, Icon, StepRow } from "@/ui";

import { stepKind } from "../traces/stepKinds";
import { netChanges, type RecordEffect } from "./model/changes";
import { callPath, chainOfStep, type CallTree } from "./model/callTree";
import { formatValue } from "./model/values";
import styles from "./StepDetails.module.css";

const NOT_DETERMINED = "not determined";
const ORM_KINDS = new Set(["orm_create", "orm_write", "orm_unlink"]);

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
  tree,
  onSelect,
}: {
  step: Step;
  tree: CallTree;
  onSelect: (id: string) => void;
}) {
  const path = callPath(tree, step.id);
  const current = tree.nodeOfStep.get(step.id);
  return (
    <ol className={styles.path} aria-label="Call path">
      {path.map((id) => {
        const node = tree.nodes.get(id);
        const head = node?.chain[0];
        if (!node || !head) return null;
        const kind = stepKind(head.kind);
        return (
          <li key={id}>
            <button
              type="button"
              className={[styles.pathItem, id === current ? styles.pathCurrent : ""]
                .join(" ")
                .trim()}
              aria-current={id === current ? "step" : undefined}
              onClick={() => {
                onSelect(id);
              }}
            >
              <StepRow
                kindIcon={kind.icon}
                kindLabel={kind.label}
                kindTone={kind.tone}
                model={head.model}
                method={head.method}
                module={head.module}
                chain={node.chain.map((layer) => layer.module)}
                duration={formatDuration(head.duration_ms)}
                changes={node.ownChanges}
                failed={node.failed}
              />
            </button>
          </li>
        );
      })}
    </ol>
  );
}

/** The implementations this call ran through, along the MRO, and whether each passed on. */
function ImplementationChain({
  step,
  chain,
  onSelect,
}: {
  step: Step;
  chain: Step[];
  onSelect: (id: string) => void;
}) {
  const last = chain[chain.length - 1];
  // Only the ORM methods are known to have a core implementation below every module; for
  // other methods the last layer not calling super() is simply the base implementation.
  const stopsEarly =
    last !== undefined &&
    ORM_KINDS.has(last.kind) &&
    last.calls_super === false &&
    last.module !== null;
  return (
    <>
      <ol className={styles.chain} aria-label="Implementation chain">
        {chain.map((layer) => (
          <li key={layer.id}>
            <button
              type="button"
              className={[styles.layer, layer.id === step.id ? styles.layerCurrent : ""]
                .join(" ")
                .trim()}
              aria-current={layer.id === step.id ? "step" : undefined}
              onClick={() => {
                onSelect(layer.id);
              }}
            >
              <span className={styles.layerPosition}>
                {layer.mro_position === null ? "?" : String(layer.mro_position)}
              </span>
              <code className={styles.layerModule}>{layer.module ?? "core"}</code>
              <span
                className={
                  layer.calls_super === false && layer !== last ? styles.superNo : styles.superText
                }
              >
                {layer.calls_super === null
                  ? NOT_DETERMINED
                  : layer.calls_super
                    ? "calls super()"
                    : "no super()"}
              </span>
              <span className={styles.layerDuration}>{formatDuration(layer.duration_ms)}</span>
            </button>
          </li>
        ))}
      </ol>
      {stopsEarly ? (
        <p className={styles.hint}>
          <code>{last.module}</code> does not call <code>super()</code>: implementations further
          down the MRO, including Odoo core, did not run for this call.
        </p>
      ) : null}
    </>
  );
}

export interface StepDetailsPaneProps {
  step: Step | null;
  index: TraceIndex;
  tree: CallTree;
  onSelect: (id: string) => void;
}

/**
 * Everything about the selected step in one column: who implements it, what the call
 * changed (including the calls it made), its arguments, and how it was reached.
 */
export function StepDetailsPane({ step, index, tree, onSelect }: StepDetailsPaneProps) {
  const effects = useMemo(() => (step ? netChanges(index, step.id) : []), [index, step]);
  if (!step) {
    return <p className={styles.hint}>This trace has no steps.</p>;
  }
  const kind = stepKind(step.kind);
  const fieldCount = effects.reduce((sum, record) => sum + record.fields.length, 0);
  const chain = chainOfStep(tree, step.id);
  const pathLength = callPath(tree, step.id).length;

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
        {chain.length > 1 ? (
          <Section title="Implementation chain" count={chain.length} hint="super() along the MRO">
            <ImplementationChain step={step} chain={chain} onSelect={onSelect} />
          </Section>
        ) : null}
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
        <Section title="Call path" count={pathLength} defaultOpen={false}>
          <CallPath step={step} tree={tree} onSelect={onSelect} />
        </Section>
      </div>
    </div>
  );
}
