import { ChevronDown, ChevronUp, X } from "lucide-react";
import type { KeyboardEvent } from "react";

import { IconButton, Input } from "@/ui";

import styles from "./CallSearchBar.module.css";

export interface CallSearchBarProps {
  query: string;
  onQuery: (query: string) => void;
  /** Number of matching calls. */
  count: number;
  /** Index of the match shown, or -1 before the first jump. */
  current: number;
  onNext: () => void;
  onPrevious: () => void;
  onClose: () => void;
}

/** Find calls in the tree: Enter = next match, Shift+Enter = previous, Escape = close. */
export function CallSearchBar({
  query,
  onQuery,
  count,
  current,
  onNext,
  onPrevious,
  onClose,
}: CallSearchBarProps) {
  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.preventDefault();
      if (event.shiftKey) onPrevious();
      else onNext();
    } else if (event.key === "Escape") {
      event.preventDefault();
      onClose();
    }
  };

  let status = "";
  if (query.trim()) {
    if (count === 0) status = "No calls";
    else if (current === -1) status = `${String(count)} ${count === 1 ? "call" : "calls"}`;
    else status = `${String(current + 1)} of ${String(count)}`;
  }

  return (
    <div className={styles.bar} role="search" aria-label="Search calls">
      <span className={styles.field}>
        <Input
          type="search"
          aria-label="Search calls"
          className={styles.input}
          compact
          mono
          autoFocus
          placeholder="model, method or module"
          value={query}
          onChange={(event) => {
            onQuery(event.target.value);
          }}
          onKeyDown={onKeyDown}
        />
        <span
          className={[styles.status, query.trim() && count === 0 ? styles.none : ""]
            .join(" ")
            .trim()}
          aria-live="polite"
        >
          {status}
        </span>
      </span>
      <IconButton
        icon={ChevronUp}
        label="Previous match (Shift+Enter)"
        compact
        disabled={count === 0}
        onClick={onPrevious}
      />
      <IconButton
        icon={ChevronDown}
        label="Next match (Enter)"
        compact
        disabled={count === 0}
        onClick={onNext}
      />
      <IconButton icon={X} label="Close search (Escape)" compact onClick={onClose} />
    </div>
  );
}
