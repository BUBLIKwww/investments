import type { ReactNode } from "react";

import { GlassSurface } from "@/shared/ui/GlassSurface";

import styles from "./SummaryCard.module.css";

type SummaryCardProps = {
  label: string;
  value: string;
  hint?: string;
  footer?: ReactNode;
};

export function SummaryCard({ label, value, hint, footer }: SummaryCardProps) {
  return (
    <GlassSurface variant="strong" className={styles.inner}>
      <p className={styles.label}>{label}</p>
      <p className={styles.value}>{value}</p>
      {hint ? <p className={styles.hint}>{hint}</p> : null}
      {footer}
    </GlassSurface>
  );
}
