import { Package } from "lucide-react";
import { useCallback, useMemo, useState } from "react";

import type { ModelSummary } from "@/api/types";
import { Checkbox, Icon, Input, Select, Tree, type TreeRow } from "@/ui";

import { filterModels, groupByModule, modulesOf, type ModelFilter } from "./model/registry";
import styles from "./Overview.module.css";

const GROUP = "module:";

export interface ModelListPaneProps {
  models: readonly ModelSummary[];
  filter: ModelFilter;
  onFilter: (filter: ModelFilter) => void;
  selected: string | null;
  onSelect: (model: string) => void;
}

/** Models grouped by the module that defined them; search and filters on top. */
export function ModelListPane({
  models,
  filter,
  onFilter,
  selected,
  onSelect,
}: ModelListPaneProps) {
  const visible = useMemo(() => filterModels(models, filter), [models, filter]);
  const groups = useMemo(() => groupByModule(visible), [visible]);
  const byName = useMemo(() => new Map(models.map((m) => [m.model, m])), [models]);
  const moduleOptions = useMemo(
    () => [
      { value: "", label: "All modules" },
      ...modulesOf(models).map((module) => ({ value: module, label: module })),
    ],
    [models],
  );
  // groups the user opened or closed; while searching every group is open
  const [toggled, setToggled] = useState<ReadonlySet<string>>(() => new Set());
  // keyboard position (module rows too); model rows also open the model. It only counts
  // while the same model stays selected (the graph can select another one).
  const [cursor, setCursor] = useState<{ id: string; selected: string | null } | null>(null);
  const toggle = useCallback((id: string) => {
    setToggled((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);
  const searching = filter.query.trim() !== "" || filter.module !== null;
  const selectedModule = selected === null ? null : (byName.get(selected)?.module ?? "core");

  const rows = useMemo(() => {
    const result: TreeRow[] = [];
    for (const [module, list] of groups) {
      const id = GROUP + module;
      const openByDefault = searching || module === selectedModule;
      const expanded = openByDefault !== toggled.has(id);
      result.push({ id, depth: 0, parentId: null, hasChildren: true, expanded });
      if (expanded) {
        for (const model of list) {
          result.push({
            id: model.model,
            depth: 1,
            parentId: id,
            hasChildren: false,
            expanded: false,
          });
        }
      }
    }
    return result;
  }, [groups, searching, selectedModule, toggled]);

  const counts = useMemo(
    () => new Map(groups.map(([module, list]) => [module, list.length])),
    [groups],
  );

  const renderRow = useCallback(
    (id: string) => {
      if (id.startsWith(GROUP)) {
        const module = id.slice(GROUP.length);
        return (
          <span
            className={styles.groupRow}
            onClick={() => {
              toggle(id);
            }}
          >
            <Icon icon={Package} compact />
            <code>{module}</code>
            <span className={styles.rowCount}>{counts.get(module) ?? 0}</span>
          </span>
        );
      }
      const model = byName.get(id);
      return (
        <span className={styles.modelRow} title={model?.description ?? undefined}>
          <code className={styles.modelName}>{id}</code>
          {model?.abstract ? <span className={styles.kindTag}>abstract</span> : null}
          {model?.transient ? <span className={styles.kindTag}>wizard</span> : null}
        </span>
      );
    },
    [byName, counts, toggle],
  );

  return (
    <div className={styles.pane}>
      <div className={styles.paneHeader}>
        <h2 className={styles.paneTitle}>Models</h2>
        <span className={styles.count} title={`${String(models.length)} models in the registry`}>
          {visible.length}
        </span>
      </div>
      <div className={styles.filters}>
        <Input
          type="search"
          aria-label="Search models"
          compact
          mono
          placeholder="sale.order or Sales Order"
          value={filter.query}
          onChange={(event) => {
            onFilter({ ...filter, query: event.target.value });
          }}
        />
        <Select
          aria-label="Module"
          compact
          options={moduleOptions}
          value={filter.module ?? ""}
          onChange={(event) => {
            onFilter({ ...filter, module: event.target.value || null });
          }}
        />
        <div className={styles.checks}>
          <Checkbox
            label="Abstract"
            checked={filter.showAbstract}
            onChange={(event) => {
              onFilter({ ...filter, showAbstract: event.target.checked });
            }}
          />
          <Checkbox
            label="Wizards"
            checked={filter.showTransient}
            onChange={(event) => {
              onFilter({ ...filter, showTransient: event.target.checked });
            }}
          />
        </div>
      </div>
      <div className={styles.treeArea}>
        {rows.length === 0 ? (
          <p className={styles.hint}>No models match these filters.</p>
        ) : (
          <Tree
            label="Models"
            rows={rows}
            renderRow={renderRow}
            selectedId={
              cursor !== null &&
              cursor.selected === selected &&
              rows.some((r) => r.id === cursor.id)
                ? cursor.id
                : selected
            }
            onSelect={(id) => {
              const isModel = !id.startsWith(GROUP);
              setCursor({ id, selected: isModel ? id : selected });
              if (isModel) onSelect(id);
            }}
            onToggle={toggle}
          />
        )}
      </div>
    </div>
  );
}
