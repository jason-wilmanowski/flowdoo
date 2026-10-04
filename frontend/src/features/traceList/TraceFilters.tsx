import { RefreshCw } from "lucide-react";
import { useState, type SubmitEvent } from "react";

import type { TraceListQuery } from "@/api/types";
import { Button, IconButton, Input, Select, Spinner, Toolbar, ToolbarSpacer } from "@/ui";

import styles from "./TraceList.module.css";

const STATUS_OPTIONS = [
  { value: "", label: "All" },
  { value: "succeeded", label: "succeeded" },
  { value: "failed", label: "failed" },
  { value: "running", label: "running" },
  { value: "pending", label: "pending" },
] as const;

type Status = NonNullable<TraceListQuery["status"]>;
const isStatus = (value: string): value is Status =>
  STATUS_OPTIONS.some((option) => option.value === value && value !== "");

export type FilterChange = Pick<
  TraceListQuery,
  "status" | "entrypoint_model" | "entrypoint_method"
>;

export interface TraceFiltersProps {
  query: TraceListQuery;
  loading: boolean;
  onChange: (change: FilterChange) => void;
  onReload: () => void;
}

/** Status applies at once; model and method (exact names) apply on Enter or "Apply". */
export function TraceFilters({ query, loading, onChange, onReload }: TraceFiltersProps) {
  const [model, setModel] = useState(query.entrypoint_model ?? "");
  const [method, setMethod] = useState(query.entrypoint_method ?? "");
  const active = Boolean(query.status ?? query.entrypoint_model ?? query.entrypoint_method);

  const apply = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    onChange({
      entrypoint_model: model.trim() || undefined,
      entrypoint_method: method.trim() || undefined,
    });
  };

  return (
    <Toolbar>
      <form className={styles.filters} onSubmit={apply} aria-label="Filter traces">
        <Select
          label="Status"
          compact
          options={STATUS_OPTIONS}
          value={query.status ?? ""}
          onChange={(event) => {
            const value = event.target.value;
            onChange({ status: isStatus(value) ? value : undefined });
          }}
        />
        <Input
          label="Model"
          compact
          mono
          placeholder="sale.order"
          value={model}
          onChange={(event) => {
            setModel(event.target.value);
          }}
        />
        <Input
          label="Method"
          compact
          mono
          placeholder="action_confirm"
          value={method}
          onChange={(event) => {
            setMethod(event.target.value);
          }}
        />
        <Button type="submit" compact>
          Apply
        </Button>
        {active ? (
          <Button
            variant="ghost"
            compact
            onClick={() => {
              setModel("");
              setMethod("");
              onChange({
                status: undefined,
                entrypoint_model: undefined,
                entrypoint_method: undefined,
              });
            }}
          >
            Clear filters
          </Button>
        ) : null}
      </form>
      <ToolbarSpacer />
      {loading ? <Spinner label="Loading" compact /> : null}
      <IconButton
        icon={RefreshCw}
        label="Reload traces"
        compact
        disabled={loading}
        onClick={onReload}
      />
    </Toolbar>
  );
}
