import { ChevronLeft, ChevronRight } from "lucide-react";

import { IconButton } from "@/ui";

import styles from "./TraceList.module.css";

export interface TracePaginationProps {
  total: number;
  limit: number;
  offset: number;
  onOffset: (offset: number) => void;
}

export function TracePagination({ total, limit, offset, onOffset }: TracePaginationProps) {
  const first = total === 0 ? 0 : offset + 1;
  const last = Math.min(offset + limit, total);
  return (
    <div className={styles.pagination}>
      <span aria-live="polite">
        {first}–{last} of {total}
      </span>
      <IconButton
        icon={ChevronLeft}
        label="Previous page"
        compact
        disabled={offset === 0}
        onClick={() => {
          onOffset(Math.max(offset - limit, 0));
        }}
      />
      <IconButton
        icon={ChevronRight}
        label="Next page"
        compact
        disabled={last >= total}
        onClick={() => {
          onOffset(offset + limit);
        }}
      />
    </div>
  );
}
