import * as RadixTabs from "@radix-ui/react-tabs";
import type { ComponentProps } from "react";

import styles from "./Tabs.module.css";

/** Tabs with Radix behavior (arrow keys, Home/End, roles) and our styling. */
export const Tabs = RadixTabs.Root;

export function TabsList(props: ComponentProps<typeof RadixTabs.List>) {
  return <RadixTabs.List {...props} className={styles.list} />;
}

export function TabsTrigger(props: ComponentProps<typeof RadixTabs.Trigger>) {
  return <RadixTabs.Trigger {...props} className={styles.trigger} />;
}

export function TabsContent(props: ComponentProps<typeof RadixTabs.Content>) {
  return <RadixTabs.Content {...props} className={styles.content} />;
}
