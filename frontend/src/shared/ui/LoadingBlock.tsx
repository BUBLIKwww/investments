import styles from "./LoadingBlock.module.css";

type LoadingBlockProps = {
  label?: string;
};

export function LoadingBlock({ label = "Загрузка…" }: LoadingBlockProps) {
  return (
    <div className={styles.wrap} role="status" aria-live="polite">
      <div className={styles.spinner} aria-hidden="true" />
      <p className={styles.text}>{label}</p>
    </div>
  );
}
