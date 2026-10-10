import { useEffect, useId, useRef, type KeyboardEvent, type ReactNode } from "react";

import styles from "./Table.module.css";

export interface TableColumn<Row> {
  id: string;
  header: string;
  cell: (row: Row) => ReactNode;
  /** Only as wide as the content (status, times, ids); the others share the rest. */
  shrink?: boolean;
  align?: "start" | "end";
}

export interface TableProps<Row> {
  /** Accessible name, e.g. "Traces". */
  label: string;
  columns: readonly TableColumn<Row>[];
  rows: readonly Row[];
  rowId: (row: Row) => string;
  selectedId?: string | null;
  onSelect?: (id: string) => void;
  /** Enter or double-click on a row, e.g. open it. */
  onActivate?: (id: string) => void;
  /** Extra class for a row, e.g. to set some rows apart. */
  rowClassName?: (row: Row) => string | undefined;
  /** The row under the mouse pointer, or null when the pointer leaves the rows. */
  onRowHover?: (id: string | null) => void;
}

/**
 * Data table with one tab stop: arrow keys, Home and End move the selection, Enter
 * activates the selected row. Pages its data instead of virtualizing.
 */
export function Table<Row>({
  label,
  columns,
  rows,
  rowId,
  selectedId = null,
  onSelect,
  onActivate,
  rowClassName,
  onRowHover,
}: TableProps<Row>) {
  const prefix = useId();
  const domId = (id: string) => `${prefix}-row-${id}`;
  const tableRef = useRef<HTMLTableElement>(null);
  const ids = rows.map(rowId);
  const selectedIndex = selectedId === null ? -1 : ids.indexOf(selectedId);

  useEffect(() => {
    if (selectedId === null) return;
    const row = tableRef.current?.ownerDocument.getElementById(`${prefix}-row-${selectedId}`);
    row?.scrollIntoView({ block: "nearest" });
  }, [prefix, selectedId]);

  const onKeyDown = (event: KeyboardEvent<HTMLTableElement>) => {
    const last = ids.length - 1;
    if (last < 0) return;
    const targets: Record<string, number | undefined> = {
      ArrowDown: Math.min(selectedIndex + 1, last),
      ArrowUp: selectedIndex === -1 ? 0 : Math.max(selectedIndex - 1, 0),
      Home: 0,
      End: last,
    };
    const target = targets[event.key];
    if (target !== undefined) {
      event.preventDefault();
      const id = ids[target];
      if (id !== undefined) onSelect?.(id);
    } else if (event.key === "Enter" && selectedId !== null && selectedIndex !== -1) {
      event.preventDefault();
      onActivate?.(selectedId);
    }
  };

  return (
    <table
      ref={tableRef}
      className={styles.table}
      role="grid"
      aria-label={label}
      aria-readonly="true"
      aria-activedescendant={
        selectedIndex === -1 || selectedId === null ? undefined : domId(selectedId)
      }
      tabIndex={0}
      onKeyDown={onKeyDown}
    >
      <thead>
        <tr>
          {columns.map((column) => (
            <th
              key={column.id}
              scope="col"
              className={[
                column.shrink ? styles.shrink : "",
                column.align === "end" ? styles.end : "",
              ]
                .join(" ")
                .trim()}
            >
              {column.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const id = rowId(row);
          const selected = id === selectedId;
          return (
            <tr
              key={id}
              id={domId(id)}
              aria-selected={selected}
              className={
                [selected ? styles.selected : "", rowClassName?.(row) ?? ""].join(" ").trim() ||
                undefined
              }
              onClick={() => onSelect?.(id)}
              onDoubleClick={() => onActivate?.(id)}
              onMouseEnter={
                onRowHover
                  ? () => {
                      onRowHover(id);
                    }
                  : undefined
              }
              onMouseLeave={
                onRowHover
                  ? () => {
                      onRowHover(null);
                    }
                  : undefined
              }
            >
              {columns.map((column) => (
                <td
                  key={column.id}
                  className={[
                    column.shrink ? styles.shrink : "",
                    column.align === "end" ? styles.end : "",
                  ]
                    .join(" ")
                    .trim()}
                >
                  {column.cell(row)}
                </td>
              ))}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
