import { displayAncestors, type CallTree } from "./callTree";

/**
 * Calls whose `model.method` or implementing modules contain the query (case-insensitive),
 * in call order. Each word must match, so "sale write" finds sale.order.line.write.
 */
export function searchCalls(tree: CallTree, query: string): string[] {
  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length === 0) return [];
  const matches: { id: string; seq: number }[] = [];
  for (const node of tree.nodes.values()) {
    const head = node.chain[0];
    if (!head) continue;
    const text = [
      `${head.model}.${head.method}`,
      ...node.chain.map((layer) => layer.module ?? "core"),
    ]
      .join(" ")
      .toLowerCase();
    if (words.every((word) => text.includes(word))) matches.push({ id: node.id, seq: head.seq });
  }
  return matches.sort((a, b) => a.seq - b.seq).map((match) => match.id);
}

/** Rows that hold matches below them (to mark folded rows that contain results). */
export function rowsContainingMatches(tree: CallTree, matches: readonly string[]): Set<string> {
  const rows = new Set<string>();
  for (const id of matches) {
    for (const ancestor of displayAncestors(tree, id)) rows.add(ancestor);
  }
  return rows;
}
