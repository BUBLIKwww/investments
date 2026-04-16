import type { ReactNode } from "react";

import styles from "./Card.module.css";

type CardProps = {
  title: string;
  subtitle?: string;
  children?: ReactNode;
};

export function Card({ title, subtitle, children }: CardProps) {
  return (
    <div className={styles.card}>
      <h3 className={styles.title}>{title}</h3>
      {subtitle ? <p className={styles.subtitle}>{subtitle}</p> : null}
      {children}
    </div>
  );
}
