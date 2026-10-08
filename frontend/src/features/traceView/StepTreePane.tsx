import { Layers, Search } from "lucide-react";
import { useCallback, useMemo, useState } from "react";

import { formatDuration } from "@/lib/format";
import { Button, Icon, StepRow, Tree } from "@/ui";

import { useShortcut } from "@/app/shortcuts/shortcutContext";

import { stepKind } from "../traces/stepKinds";
import { CallSearchBar } from "./CallSearchBar";
import {
  expandAll,
  firstStepOfRow,
  isExpanded,
  rowForStep,
  visibleCallRows,
  type CallTree,
} from "./model/callTree";
import { rowsContainingMatches, searchCalls } from "./model/search";
import styles from "./TraceView.module.css";

export interface StepTreePaneProps {
  tree: CallTree;
  stepCount: number;
  /** Rows whose expansion differs from the default (relevant paths open). */
  toggled: ReadonlySet<string>;
  onToggled: (toggled: ReadonlySet<string>) => void;
  /** The step at the replay position. */
  selectedStepId: string | null;
  onSelectStep: (stepId: string) => void;
  /** Move the replay to a call and unfold the tree to its row (search results). */
  onJumpToCall: (nodeId: string) => void;
}

/**
 * The call tree: one row per call (super chains merged), only the paths to changes and
 * errors open at first, irrelevant runs folded. The row holding the replay position is
 * selected; replaying does not unfold the tree.
 */
export function StepTreePane({
  tree,
  stepCount,
  toggled,
  onToggled,
  selectedStepId,
  onSelectStep,
  onJumpToCall,
}: StepTreePaneProps) {
  const rows = useMemo(() => visibleCallRows(tree, toggled), [tree, toggled]);

  // search: matches are calls (node ids = their first step), in call order
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [current, setCurrent] = useState(-1);
  const matches = useMemo(() => searchCalls(tree, query), [tree, query]);
  const matchSet = useMemo(() => new Set(matches), [matches]);
  const holdsMatches = useMemo(() => rowsContainingMatches(tree, matches), [tree, matches]);
  const goToMatch = (index: number) => {
    if (matches.length === 0) return;
    const next = (index + matches.length) % matches.length;
    setCurrent(next);
    const id = matches[next];
    if (id !== undefined) onJumpToCall(id);
  };
  const closeSearch = () => {
    setSearchOpen(false);
    setQuery("");
    setCurrent(-1);
  };
  useShortcut(
    { id: "search-calls", key: "/", label: "/", description: "Search calls", group: "Trace" },
    () => {
      setSearchOpen(true);
    },
  );
  const selectedRow = selectedStepId === null ? null : rowForStep(tree, toggled, selectedStepId);

  const onToggle = useCallback(
    (id: string) => {
      const next = new Set(toggled);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      onToggled(next);
    },
    [toggled, onToggled],
  );

  const onSelect = useCallback(
    (rowId: string) => {
      const stepId = firstStepOfRow(tree, rowId);
      if (stepId !== null) onSelectStep(stepId);
    },
    [tree, onSelectStep],
  );

  const renderContent = useCallback(
    (id: string) => {
      const group = tree.groups.get(id);
      if (group) {
        return (
          <span className={styles.groupRow}>
            <Icon icon={Layers} compact />
            <span>
              {group.members.length} calls{" "}
              {group.model ? (
                <>
                  in <code>{group.model}</code>
                </>
              ) : (
                "without changes"
              )}
            </span>
            <span className={styles.groupSteps}>{group.stepCount} steps</span>
          </span>
        );
      }
      const layer = tree.layers.get(id);
      if (layer) {
        const { step } = layer;
        const last = tree.nodes.get(layer.nodeId)?.chain.at(-1)?.id === step.id;
        return (
          <span className={styles.layerRow}>
            <span className={styles.layerMro} title="Position in the MRO (0 = most derived)">
              {step.mro_position ?? "?"}
            </span>
            <code className={styles.layerModule}>{step.module ?? "core"}</code>
            <span
              className={
                step.calls_super === false && !last ? styles.layerSuperNo : styles.layerSuper
              }
            >
              {step.calls_super === null
                ? "super() not determined"
                : step.calls_super
                  ? "calls super()"
                  : "no super()"}
            </span>
            {step.changes.length > 0 ? (
              <span
                className={styles.layerChanges}
                title={`${String(step.changes.length)} field changes`}
              >
                Δ{step.changes.length}
              </span>
            ) : null}
            <span className={styles.groupSteps}>{formatDuration(step.duration_ms)}</span>
          </span>
        );
      }
      const node = tree.nodes.get(id);
      const head = node?.chain[0];
      if (!node || !head) return null;
      const kind = stepKind(head.kind);
      return (
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
      );
    },
    [tree],
  );

  const renderRow = useCallback(
    (id: string) => {
      const content = renderContent(id);
      const hidden = holdsMatches.has(id) && !isExpanded(tree, toggled, id);
      if (!matchSet.has(id) && !hidden) return content;
      return (
        <span className={matchSet.has(id) ? styles.match : styles.matchRow}>
          {content}
          {hidden ? (
            <span className={styles.matchDot} title="Contains search results">
              <span className={styles.visuallyHidden}>contains search results</span>
            </span>
          ) : null}
        </span>
      );
    },
    [holdsMatches, matchSet, toggled, tree, renderContent],
  );

  return (
    <div className={styles.pane}>
      <div className={styles.paneHeader}>
        <h2 className={styles.paneTitle}>Calls</h2>
        <span className={styles.count} title={`${String(stepCount)} recorded steps`}>
          {tree.nodes.size}
        </span>
        <span className={styles.spacer} />
        <Button
          variant="ghost"
          compact
          icon={Search}
          aria-expanded={searchOpen}
          title="Search calls (/)"
          onClick={() => {
            if (searchOpen) closeSearch();
            else setSearchOpen(true);
          }}
        >
          Search
        </Button>
        <Button
          variant="ghost"
          compact
          onClick={() => {
            onToggled(expandAll(tree));
          }}
        >
          Expand all
        </Button>
        <Button
          variant="ghost"
          compact
          disabled={toggled.size === 0}
          onClick={() => {
            onToggled(new Set());
          }}
        >
          Relevant only
        </Button>
      </div>
      {searchOpen ? (
        <CallSearchBar
          query={query}
          onQuery={(next) => {
            setQuery(next);
            setCurrent(-1);
          }}
          count={matches.length}
          current={current}
          onNext={() => {
            goToMatch(current + 1);
          }}
          onPrevious={() => {
            goToMatch(current === -1 ? -1 : current - 1);
          }}
          onClose={closeSearch}
        />
      ) : null}
      <div className={styles.treeArea}>
        <Tree
          label="Calls"
          rows={rows}
          renderRow={renderRow}
          selectedId={selectedRow}
          onSelect={onSelect}
          onToggle={onToggle}
        />
      </div>
    </div>
  );
}
