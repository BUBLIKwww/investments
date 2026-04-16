import { GlassSurface } from "@/shared/ui/GlassSurface";

import styles from "./LoadingBlock.module.css";

type LoadingBlockProps = {
  label?: string;
};

export function LoadingBlock({ label = "Загрузка…" }: LoadingBlockProps) {
  return (
    <GlassSurface className={styles.panel} role="status" aria-live="polite">
      <div className={styles.spinner} aria-hidden="true" />
      <p className={styles.text}>{label}</p>
    </GlassSurface>
  );
}
