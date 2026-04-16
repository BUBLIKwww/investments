import type { ReactNode } from "react";

import { Button } from "@/shared/ui/Button";

import styles from "./ErrorBlock.module.css";

type ErrorBlockProps = {
  title?: string;
  message: string;
  onRetry?: () => void;
  children?: ReactNode;
};

export function ErrorBlock({ title = "Не удалось загрузить", message, onRetry, children }: ErrorBlockProps) {
  return (
    <div className={styles.wrap} role="alert">
      <p className={styles.title}>{title}</p>
      <p className={styles.text}>{message}</p>
      <div className={styles.actions}>
        {onRetry ? (
          <Button type="button" variant="secondary" size="sm" onClick={onRetry}>
            Повторить
          </Button>
        ) : null}
        {children}
      </div>
    </div>
  );
}
