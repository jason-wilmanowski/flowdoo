// avoid-ai-design-ignore: I3 (Lucide is the only icon set; Check confirms a copy)
import { Check, ChevronDown, ChevronUp, Copy } from "lucide-react";
import { useEffect, useState } from "react";

import styles from "./CodeValue.module.css";
import { IconButton } from "./IconButton";

/** How long "copied" stays visible. */
const COPIED_FEEDBACK_MS = 1500;
/** Longer values (or multi-line ones) start collapsed to one line. */
export const COLLAPSE_AFTER_CHARS = 80;

export interface CodeValueProps {
  /** Shown exactly as given (technical identifiers, values, JSON). */
  value: string;
  /** Accessible name of the copy button target, e.g. "args summary". */
  label?: string;
  /** Background for diffs: old (removed) or new (added) value. */
  tone?: "plain" | "old" | "new";
}

/** A technical value in mono: truncated to one line when long, expandable, copyable. */
export function CodeValue({ value, label = "value", tone = "plain" }: CodeValueProps) {
  const long = value.length > COLLAPSE_AFTER_CHARS || value.includes("\n");
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => {
      setCopied(false);
    }, COPIED_FEEDBACK_MS);
    return () => {
      clearTimeout(timer);
    };
  }, [copied]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
    } catch {
      setCopied(false); // clipboard not available: nothing to report but the missing feedback
    }
  }

  return (
    <span className={[styles.codeValue, styles[tone]].join(" ")}>
      <code className={long && !expanded ? styles.truncated : styles.full}>{value}</code>
      {long ? (
        <IconButton
          icon={expanded ? ChevronUp : ChevronDown}
          label={expanded ? `Collapse ${label}` : `Expand ${label}`}
          aria-expanded={expanded}
          compact
          onClick={() => {
            setExpanded((open) => !open);
          }}
        />
      ) : null}
      <IconButton
        icon={copied ? Check : Copy}
        label={copied ? `Copied ${label}` : `Copy ${label}`}
        compact
        onClick={() => {
          void copy();
        }}
      />
      <span className={styles.visuallyHidden} aria-live="polite">
        {copied ? "Copied" : ""}
      </span>
    </span>
  );
}
