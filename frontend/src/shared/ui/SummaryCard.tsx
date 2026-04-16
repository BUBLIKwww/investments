import type { ReactNode } from "react";

import styles from "./SummaryCard.module.css";

type SummaryCardProps = {
  label: string;
  value: string;
  hint?: string;
  footer?: ReactNode;
};

export function SummaryCard({ label, value, hint, footer }: SummaryCardProps) {
  return (
    <div className={styles.card}>
      <p className={styles.label}>{label}</p>
      <p className={styles.value}>{value}</p>
      {hint ? <p className={styles.hint}>{hint}</p> : null}
      {footer}
    </div>
  );
}
