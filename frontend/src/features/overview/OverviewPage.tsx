import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { useStore } from "zustand";

import { useStores } from "@/app/appContext";
import { Button, EmptyState, Skeleton, SplitPanel } from "@/ui";

import { DEFAULT_NEIGHBOR_OPTIONS } from "./model/neighborhood";
import { DEFAULT_FILTER } from "./model/registry";
import { ModelDetailsPane } from "./ModelDetailsPane";
import { ModelGraphPane } from "./ModelGraphPane";
import { ModelListPane } from "./ModelListPane";
import styles from "./Overview.module.css";

/** /overview and /overview/:model: the model registry of the connected Odoo. */
export function OverviewPage() {
  const { model: selected = null } = useParams();
  const navigate = useNavigate();
  const { registry } = useStores();
  const models = useStore(registry, (state) => state.models);
  const phase = useStore(registry, (state) => state.phase);
  const error = useStore(registry, (state) => state.error);
  const load = useStore(registry, (state) => state.load);
  const describe = useStore(registry, (state) => state.describe);
  const shown = useStore(registry, (state) => state.model);
  const detail = useStore(registry, (state) => state.detail);
  const detailPhase = useStore(registry, (state) => state.detailPhase);
  const detailError = useStore(registry, (state) => state.detailError);
  const [filter, setFilter] = useState(DEFAULT_FILTER);
  const [options, setOptions] = useState(DEFAULT_NEIGHBOR_OPTIONS);
  // the model pointed out from the details, valid for the model it was pointed out on
  const [highlight, setHighlight] = useState<{ on: string | null; model: string | null }>({
    on: null,
    model: null,
  });

  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    if (selected !== null) void describe(selected);
  }, [selected, describe]);

  const select = (model: string) => {
    void navigate(`/overview/${encodeURIComponent(model)}`);
  };

  if (phase === "error" && error) {
    return (
      <main className={styles.island}>
        <EmptyState
          tone="danger"
          message={`Could not load the models of Odoo: ${error.message}`}
          action={
            <Button
              onClick={() => {
                void load(true);
              }}
            >
              Retry
            </Button>
          }
        />
      </main>
    );
  }
  if (!models) {
    return (
      <main className={styles.island}>
        <Skeleton rows={10} label="Loading models" />
      </main>
    );
  }

  const current = selected !== null && shown === selected;
  return (
    <div className={styles.page}>
      <SplitPanel
        id="overview"
        start={{
          label: "Models",
          content: (
            <ModelListPane
              models={models}
              filter={filter}
              onFilter={setFilter}
              selected={selected}
              onSelect={select}
            />
          ),
          defaultWidth: "var(--panel-left-w)",
          minWidth: 220,
          maxWidth: 560,
        }}
        end={{
          label: "Model details",
          content: (
            <ModelDetailsPane
              key={selected ?? ""}
              models={models}
              detail={current ? detail : null}
              loading={current && detailPhase === "loading"}
              error={current && detailPhase === "error" ? detailError : null}
              onSelect={select}
              onHighlight={(model) => {
                setHighlight({ on: selected, model });
              }}
            />
          ),
          defaultWidth: "calc(var(--panel-right-w) * 1.3)",
          minWidth: 320,
          maxWidth: 820,
        }}
      >
        <ModelGraphPane
          models={models}
          selected={selected}
          options={options}
          highlight={highlight.on === selected ? highlight.model : null}
          onOptions={setOptions}
          onSelect={select}
        />
      </SplitPanel>
    </div>
  );
}
