import { Link2 } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";

import type { AppError } from "@/api/errors";
import type { ModelDetail, ModelField, ModelSummary } from "@/api/types";
import { Badge, EmptyState, Icon, Input, Skeleton, Table, type TableColumn } from "@/ui";

import { incomingRelations } from "./model/registry";
import styles from "./Overview.module.css";

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className={styles.fact}>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function ModelLink({ model, onSelect }: { model: string; onSelect: (model: string) => void }) {
  return (
    <button
      type="button"
      className={styles.modelLink}
      onClick={() => {
        onSelect(model);
      }}
    >
      {model}
    </button>
  );
}

function flagsOf(field: ModelField): string[] {
  const flags: string[] = [];
  if (field.required) flags.push("required");
  if (field.related) flags.push("related");
  else if (field.compute) flags.push(field.stored ? "computed, stored" : "computed");
  else if (!field.stored) flags.push("not stored");
  if (field.readonly && !field.compute && !field.related) flags.push("readonly");
  return flags;
}

export interface ModelDetailsPaneProps {
  models: readonly ModelSummary[];
  detail: ModelDetail | null;
  loading: boolean;
  error: AppError | null;
  onSelect: (model: string) => void;
  /** Point out a model in the graph (the target of a field), or null. */
  onHighlight: (model: string | null) => void;
}

/** One model: where it comes from, what it inherits, its fields and who links to it. */
export function ModelDetailsPane({
  models,
  detail,
  loading,
  error,
  onSelect,
  onHighlight,
}: ModelDetailsPaneProps) {
  const [fieldQuery, setFieldQuery] = useState("");
  // the field chosen with click or arrow keys; hovering shows another one for a moment
  const [chosenField, setChosenField] = useState<string | null>(null);
  const targetOf = (name: string | null) =>
    name === null ? null : (detail?.fields.find((f) => f.name === name)?.target ?? null);
  const incoming = useMemo(
    () => (detail ? incomingRelations(models, detail.model) : []),
    [models, detail],
  );
  const fields = useMemo(() => {
    const words = fieldQuery.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const all = detail?.fields ?? [];
    return all
      .filter((f) => {
        const text =
          `${f.name} ${f.string ?? ""} ${f.type} ${f.target ?? ""} ${f.module ?? ""}`.toLowerCase();
        return words.every((word) => text.includes(word));
      })
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [detail, fieldQuery]);

  const columns = useMemo<TableColumn<ModelField>[]>(
    () => [
      {
        id: "name",
        header: "Field",
        cell: (field) => (
          <span className={styles.fieldName} title={field.string ?? undefined}>
            {field.target ? (
              <span className={styles.linkMark} title={`Links to ${field.target}`}>
                <Icon icon={Link2} compact label={`links to ${field.target}`} />
              </span>
            ) : null}
            <code>{field.name}</code>
          </span>
        ),
      },
      {
        id: "type",
        header: "Type",
        shrink: true,
        cell: (field) =>
          field.target ? (
            <span className={styles.fieldType}>
              <code>{field.type}</code>
              <ModelLink model={field.target} onSelect={onSelect} />
            </span>
          ) : (
            <code className={styles.muted}>{field.type}</code>
          ),
      },
      {
        id: "flags",
        header: "",
        shrink: true,
        cell: (field) => (
          <span className={styles.flags}>
            {flagsOf(field).map((flag) => (
              <span key={flag} className={flag === "required" ? styles.flagStrong : styles.flag}>
                {flag}
              </span>
            ))}
          </span>
        ),
      },
      {
        id: "module",
        header: "Module",
        shrink: true,
        cell: (field) => <code className={styles.muted}>{field.module ?? "core"}</code>,
      },
    ],
    [onSelect],
  );

  if (loading) return <Skeleton rows={8} label="Loading model" />;
  if (error) return <EmptyState tone="danger" message={error.message} />;
  if (!detail) {
    return (
      <p className={styles.hint}>
        Fields, inheritance and relations of the selected model show here.
      </p>
    );
  }

  return (
    <div className={styles.details}>
      <header className={styles.detailsHeader}>
        <h2 className={styles.detailsTitle}>{detail.model}</h2>
        {detail.description ? <p className={styles.description}>{detail.description}</p> : null}
        <div className={styles.badges}>
          {detail.abstract ? <Badge>abstract</Badge> : null}
          {detail.transient ? <Badge tone="warning">wizard</Badge> : null}
          <Badge mono>{detail.fields.length} fields</Badge>
        </div>
        <dl className={styles.facts}>
          <Fact label="Defined in">
            <code>{detail.module ?? "core"}</code>
          </Fact>
          <Fact label="Extended by">
            {detail.modules.length > 1 ? (
              <code>{detail.modules.slice(0, -1).join(" → ")}</code>
            ) : (
              <span className={styles.muted}>no other module</span>
            )}
          </Fact>
          <Fact label="Inherits from">
            {detail.parents.length > 0 ? (
              <span className={styles.chips}>
                {detail.parents.map((parent) => (
                  <ModelLink key={parent} model={parent} onSelect={onSelect} />
                ))}
              </span>
            ) : (
              <span className={styles.muted}>nothing</span>
            )}
          </Fact>
          {Object.keys(detail.delegates).length > 0 ? (
            <Fact label="Delegates to">
              <span className={styles.chips}>
                {Object.entries(detail.delegates).map(([model, field]) => (
                  <span key={model} className={styles.delegate}>
                    <ModelLink model={model} onSelect={onSelect} />
                    <code className={styles.muted}>via {field}</code>
                  </span>
                ))}
              </span>
            </Fact>
          ) : null}
        </dl>
      </header>

      <section className={styles.section} aria-label="Fields">
        <div className={styles.sectionHeader}>
          <h3 className={styles.sectionTitle}>Fields</h3>
          <span className={styles.count}>{fields.length}</span>
          <Input
            type="search"
            aria-label="Search fields"
            compact
            mono
            className={styles.fieldSearch}
            placeholder="name, type or module"
            value={fieldQuery}
            onChange={(event) => {
              setFieldQuery(event.target.value);
            }}
          />
        </div>
        <Table
          label="Fields"
          columns={columns}
          rows={fields}
          rowId={(field) => field.name}
          rowClassName={(field) => (field.target ? styles.relationRow : undefined)}
          selectedId={chosenField}
          onSelect={(name) => {
            setChosenField(name);
            onHighlight(targetOf(name));
          }}
          onRowHover={(name) => {
            onHighlight(targetOf(name ?? chosenField));
          }}
        />
      </section>

      <section className={styles.section} aria-label="Linked from">
        <div className={styles.sectionHeader}>
          <h3 className={styles.sectionTitle}>Linked from</h3>
          <span className={styles.count}>{incoming.length}</span>
        </div>
        {incoming.length === 0 ? (
          <p className={styles.hint}>No other model links to {detail.model}.</p>
        ) : (
          <ul className={styles.incoming}>
            {incoming.map((relation) => (
              <li
                key={`${relation.from}.${relation.field}`}
                onMouseEnter={() => {
                  onHighlight(relation.from);
                }}
                onMouseLeave={() => {
                  onHighlight(targetOf(chosenField));
                }}
              >
                <ModelLink model={relation.from} onSelect={onSelect} />
                <code className={styles.muted}>
                  .{relation.field} ({relation.type})
                </code>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
