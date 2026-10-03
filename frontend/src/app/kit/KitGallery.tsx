import type { Edge } from "@xyflow/react";
import { AlertTriangle, Copy, Moon, Pause, Play, StepForward, Sun } from "lucide-react";
import { useState } from "react";

import { chooseTheme, initialTheme, type Theme } from "@/lib/theme";
import {
  Badge,
  Button,
  CodeValue,
  EmptyState,
  GraphCanvas,
  IconButton,
  Kbd,
  Skeleton,
  Spinner,
  SplitPanel,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  TooltipProvider,
  type GraphNodeType,
} from "@/ui";

import styles from "./KitGallery.module.css";

// Fixed example nodes; positions are hand-placed (no layout algorithm in the kit).
const NODES: GraphNodeType[] = [
  {
    id: "a",
    type: "flowdoo",
    position: { x: 0, y: 0 },
    data: { model: "sale.order", module: "sale", detail: "action_confirm" },
  },
  {
    id: "b",
    type: "flowdoo",
    position: { x: 340, y: 0 },
    data: { model: "sale.order", module: "sale_stock", detail: "_action_confirm", active: true },
  },
  {
    id: "c",
    type: "flowdoo",
    position: { x: 680, y: 120 },
    data: { model: "stock.picking", module: null, detail: "create" },
  },
];
const EDGES: Edge[] = [
  { id: "a-b", source: "a", target: "b" },
  { id: "b-c", source: "b", target: "c" },
];

const LONG_VALUE =
  "{'partner_id': 12, 'order_line': [(0, 0, {'product_id': 38, 'product_uom_qty': 3.0}), (0, 0, {'product_id': 6})], 'note': 'deliver before noon'}";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className={styles.section} aria-labelledby={`kit-${title}`}>
      <h2 id={`kit-${title}`} className={styles.title}>
        {title}
      </h2>
      <div className={styles.row}>{children}</div>
    </section>
  );
}

/** Development-only gallery of the UI primitives (/_kit). Not part of production builds. */
export function KitGallery() {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  function switchTheme(next: Theme) {
    chooseTheme(next);
    setTheme(next);
  }

  return (
    <TooltipProvider>
      <div className={styles.kit}>
        <header className={styles.header}>
          <h1 className={styles.heading}>UI kit</h1>
          <Button
            compact
            icon={theme === "dark" ? Sun : Moon}
            onClick={() => {
              switchTheme(theme === "dark" ? "light" : "dark");
            }}
          >
            {theme === "dark" ? "Light theme" : "Dark theme"}
          </Button>
        </header>

        <Section title="Button">
          <Button variant="primary">Start trace</Button>
          <Button>Reload</Button>
          <Button variant="ghost">Cancel</Button>
          <Button variant="primary" compact>
            Compact
          </Button>
          <Button icon={Copy}>With icon</Button>
          <Button variant="primary" loading>
            Recording
          </Button>
          <Button disabled>Disabled</Button>
          <Button variant="ghost" disabled>
            Disabled ghost
          </Button>
        </Section>

        <Section title="IconButton">
          <IconButton icon={StepForward} label="Next step" />
          <IconButton icon={Play} label="Play" variant="secondary" />
          <IconButton icon={Pause} label="Pause" compact />
          <IconButton icon={Copy} label="Copy" disabled />
        </Section>

        <Section title="Badge">
          <Badge>neutral</Badge>
          <Badge mono>sale_stock</Badge>
          <Badge tone="accent">running</Badge>
          <Badge tone="success">succeeded</Badge>
          <Badge tone="warning" icon={AlertTriangle}>
            Blocked
          </Badge>
          <Badge tone="danger">failed</Badge>
        </Section>

        <Section title="Kbd">
          <span>
            <Kbd>Space</Kbd> play or pause
          </span>
          <span>
            <Kbd>←</Kbd> <Kbd>→</Kbd> step
          </span>
          <span>
            <Kbd>?</Kbd> shortcuts
          </span>
        </Section>

        <Section title="CodeValue">
          <CodeValue value="sale.order" label="model" />
          <CodeValue value="draft" label="old value" tone="old" />
          <CodeValue value="sale" label="new value" tone="new" />
          <div className={styles.wide}>
            <CodeValue value={LONG_VALUE} label="args summary" />
          </div>
        </Section>

        <Section title="Tabs">
          <Tabs defaultValue="changes" className={styles.wide}>
            <TabsList aria-label="Step details">
              <TabsTrigger value="changes">Changes</TabsTrigger>
              <TabsTrigger value="overrides">Overrides</TabsTrigger>
              <TabsTrigger value="raw">Arguments</TabsTrigger>
            </TabsList>
            <TabsContent value="changes">Field changes of the selected step.</TabsContent>
            <TabsContent value="overrides">Implementations along the MRO.</TabsContent>
            <TabsContent value="raw">Shortened arguments and return value.</TabsContent>
          </Tabs>
        </Section>

        <Section title="Loading, empty and error states">
          <Spinner label="Loading trace" />
          <div className={styles.box}>
            <Skeleton rows={4} label="Loading traces" />
          </div>
          <div className={styles.box}>
            <EmptyState
              message="No traces yet. Start one from an entrypoint such as sale.order.action_confirm."
              action={<Button variant="primary">Start trace</Button>}
            />
          </div>
          <div className={styles.box}>
            <EmptyState
              tone="danger"
              message="Could not reach the API at http://localhost:8000. Check that the backend is running."
              action={<Button>Retry</Button>}
            />
          </div>
        </Section>

        <Section title="SplitPanel">
          <div className={styles.split}>
            <SplitPanel
              id="kit"
              start={{
                label: "Steps",
                content: <p className={styles.pad}>Left panel</p>,
                defaultWidth: "var(--panel-left-w)",
                minWidth: 180,
                maxWidth: 480,
              }}
              end={{
                label: "Details",
                content: <p className={styles.pad}>Right panel</p>,
                defaultWidth: "var(--panel-right-w)",
                minWidth: 240,
                maxWidth: 560,
              }}
            >
              <p className={styles.pad}>
                Main area. Drag or focus a handle and use ←/→, Home/End, Enter.
              </p>
            </SplitPanel>
          </div>
        </Section>

        <Section title="GraphCanvas and GraphNode">
          <div className={styles.graph}>
            <GraphCanvas label="Example call graph" nodes={NODES} edges={EDGES} />
          </div>
        </Section>
      </div>
    </TooltipProvider>
  );
}
