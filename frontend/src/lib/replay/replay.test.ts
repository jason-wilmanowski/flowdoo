// @vitest-environment node
import { FIXTURE_NAMES, loadFixture } from "@/datasource/fixtures/catalog";
import type { Step } from "@/generated/trace";
import {
  activePath,
  childrenOf,
  clampCursor,
  cursorOf,
  firstStep,
  indexTrace,
  isAtEnd,
  lastStep,
  nextStep,
  pathTo,
  previousStep,
  stepAt,
} from "@/lib/replay";

const fixtures = await Promise.all(
  FIXTURE_NAMES.map(async (name) => [name, await loadFixture(name)] as const),
);

function shuffled<T>(items: readonly T[]): T[] {
  // deterministic: reverse and interleave, so no test depends on randomness
  const reversed = [...items].reverse();
  return reversed.filter((_, i) => i % 2 === 0).concat(reversed.filter((_, i) => i % 2 === 1));
}

describe.each(fixtures)("%s", (_name, payload) => {
  const index = indexTrace(payload);

  it("orders steps by seq", () => {
    const seqs = index.ordered.map((s) => s.seq);
    expect(seqs).toEqual([...seqs].sort((a, b) => a - b));
    expect(new Set(seqs).size).toBe(payload.steps.length);
  });

  it("does not depend on the order of the steps array", () => {
    const again = indexTrace({ steps: shuffled(payload.steps) });
    expect(again.ordered.map((s) => s.id)).toEqual(index.ordered.map((s) => s.id));
    expect([...again.childrenById]).toEqual([...index.childrenById]);
  });

  it("builds the call tree from parent_id", () => {
    expect(index.roots).toEqual(index.ordered.filter((s) => s.parent_id === null).map((s) => s.id));
    expect(index.depthById.size).toBe(payload.steps.length); // every step is reachable
    for (const step of payload.steps) {
      if (step.parent_id !== null) {
        expect(childrenOf(index, step.parent_id)).toContain(step.id);
        expect(index.depthById.get(step.id)).toBe(index.depthById.get(step.parent_id)! + 1);
      }
    }
    for (const [, ids] of index.childrenById) {
      const seqs = ids.map((id) => index.byId.get(id)!.seq);
      expect(seqs).toEqual([...seqs].sort((a, b) => a - b));
    }
  });

  it("navigates within bounds", () => {
    const n = payload.steps.length;
    expect(firstStep(n)).toBe(0);
    expect(lastStep(n)).toBe(n - 1);
    expect(previousStep(0, n)).toBe(0);
    expect(nextStep(n - 1, n)).toBe(n - 1);
    expect(nextStep(0, n)).toBe(Math.min(1, n - 1));
    expect(clampCursor(10_000, n)).toBe(n - 1);
    expect(clampCursor(-5, n)).toBe(0);
    expect(isAtEnd(n - 1, n)).toBe(true);
  });

  it("gives the active path from the top-level step to the cursor", () => {
    const last = lastStep(payload.steps.length);
    const path = activePath(index, last);
    const step = stepAt(index, last)!;

    expect(path.at(-1)).toBe(step.id);
    expect(index.byId.get(path[0]!)!.parent_id).toBeNull();
    expect(path).toHaveLength(index.depthById.get(step.id)! + 1);
    expect(cursorOf(index, step.id)).toBe(last);
  });
});

describe("edge cases", () => {
  const step = (id: string, seq: number, parent: string | null): Step => ({
    id,
    parent_id: parent,
    seq,
    kind: "method_call",
    model: "res.partner",
    method: "write",
    module: "base",
    mro_position: 0,
    calls_super: false,
    record_ids: [],
    args_summary: null,
    return_summary: null,
    changes: [],
    duration_ms: 0,
    error: null,
  });

  it("a trace without steps has no cursor", () => {
    const index = indexTrace({ steps: [] });

    expect(firstStep(0)).toBeNull();
    expect(nextStep(null, 0)).toBeNull();
    expect(activePath(index, null)).toEqual([]);
    expect(index.roots).toEqual([]);
  });

  it("a step whose parent is missing becomes a root instead of disappearing", () => {
    const index = indexTrace({ steps: [step("s2", 2, "gone"), step("s1", 1, null)] });

    expect(index.roots).toEqual(["s1", "s2"]);
    expect(index.depthById.get("s2")).toBe(0);
  });

  it("pathTo of an unknown id is empty", () => {
    expect(pathTo(indexTrace({ steps: [step("s1", 1, null)] }), "nope")).toEqual([]);
  });
});

describe("performance with the 879-step recording", () => {
  const recorded = fixtures.find(([name]) => name === "recorded-sale-order-action-confirm")![1];

  function best(run: () => void): number {
    let fastest = Infinity;
    for (let i = 0; i < 5; i++) {
      const start = performance.now();
      run();
      fastest = Math.min(fastest, performance.now() - start);
    }
    return fastest;
  }

  it("indexes the trace fast", () => {
    expect(recorded.steps).toHaveLength(879);
    expect(best(() => indexTrace(recorded))).toBeLessThan(25);
  });

  it("replays every step with its active path fast", () => {
    const index = indexTrace(recorded);
    const n = index.ordered.length;
    const ms = best(() => {
      for (let cursor = firstStep(n); !isAtEnd(cursor, n); cursor = nextStep(cursor, n)) {
        activePath(index, cursor);
      }
    });
    expect(ms).toBeLessThan(25);
  });
});
