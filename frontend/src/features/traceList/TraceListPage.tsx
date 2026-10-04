import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { useStore } from "zustand";

import { useStores } from "@/app/appContext";
import { Button, EmptyState, Skeleton, SplitPanel } from "@/ui";

import { TraceDetails } from "./TraceDetails";
import { TraceFilters } from "./TraceFilters";
import styles from "./TraceList.module.css";
import { TracePagination } from "./TracePagination";
import { TraceTable } from "./TraceTable";

export const PAGE_SIZE = 25;

/** /traces: recorded traces with filters and paging; details of the selected one on the right. */
export function TraceListPage() {
  const { traceList } = useStores();
  const navigate = useNavigate();
  const query = useStore(traceList, (state) => state.query);
  const page = useStore(traceList, (state) => state.page);
  const phase = useStore(traceList, (state) => state.phase);
  const error = useStore(traceList, (state) => state.error);
  const load = useStore(traceList, (state) => state.load);
  const remove = useStore(traceList, (state) => state.remove);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    void load({ limit: PAGE_SIZE });
  }, [load]);

  const filtered = Boolean(query.status ?? query.entrypoint_model ?? query.entrypoint_method);
  const selected = page?.items.find((trace) => trace.id === selectedId) ?? null;
  const open = (id: string) => {
    void navigate(`/traces/${id}`);
  };

  let content;
  if (phase === "error" && error) {
    content = (
      <EmptyState
        tone="danger"
        message={`Could not load the traces: ${error.message}`}
        action={
          <Button
            onClick={() => {
              void load();
            }}
          >
            Retry
          </Button>
        }
      />
    );
  } else if (!page) {
    content = <Skeleton rows={8} label="Loading traces" />;
  } else if (page.total === 0 && filtered) {
    content = <EmptyState message="No traces match these filters." />;
  } else if (page.total === 0) {
    content = (
      <EmptyState message="No traces recorded yet. Record one with POST /traces of the API; starting a trace from here comes next." />
    );
  } else {
    content = (
      <TraceTable
        traces={page.items}
        selectedId={selectedId}
        onSelect={setSelectedId}
        onOpen={open}
      />
    );
  }

  return (
    <div className={styles.page}>
      <SplitPanel
        id="traces"
        end={{
          label: "Trace details",
          content: (
            <TraceDetails
              trace={selected}
              deleteError={
                phase === "ready" && error ? `Could not delete the trace: ${error.message}` : null
              }
              onDelete={async (id) => {
                await remove(id);
                setSelectedId((current) => (current === id ? null : current));
              }}
            />
          ),
          defaultWidth: "var(--panel-right-w)",
          minWidth: 280,
          maxWidth: 640,
        }}
      >
        <div className={styles.listColumn}>
          <TraceFilters
            query={query}
            loading={phase === "loading" && page !== null}
            onChange={(change) => {
              void load({ ...change, offset: 0 });
            }}
            onReload={() => {
              void load();
            }}
          />
          <div className={styles.tableArea}>{content}</div>
          {page && page.total > 0 ? (
            <TracePagination
              total={page.total}
              limit={page.limit}
              offset={page.offset}
              onOffset={(offset) => {
                void load({ offset });
              }}
            />
          ) : null}
        </div>
      </SplitPanel>
    </div>
  );
}
