import * as RadixTabs from "@radix-ui/react-tabs";
import type { ComponentProps } from "react";

import styles from "./Tabs.module.css";

const join = (own: string | undefined, extra: string | undefined) =>
  [own ?? "", extra ?? ""].join(" ").trim();

/** Tabs with Radix behavior (arrow keys, Home/End, roles) and our styling. */
export const Tabs = RadixTabs.Root;

export function TabsList(props: ComponentProps<typeof RadixTabs.List>) {
  return <RadixTabs.List {...props} className={join(styles.list, props.className)} />;
}

export function TabsTrigger(props: ComponentProps<typeof RadixTabs.Trigger>) {
  return <RadixTabs.Trigger {...props} className={join(styles.trigger, props.className)} />;
}

export function TabsContent(props: ComponentProps<typeof RadixTabs.Content>) {
  return <RadixTabs.Content {...props} className={join(styles.content, props.className)} />;
}
