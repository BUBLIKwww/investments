import type { ReactNode } from "react";

import { GlassSurface } from "@/shared/ui/GlassSurface";

import styles from "./EmptyState.module.css";

type EmptyStateProps = {
  title: string;
  description: string;
  icon?: ReactNode;
  actions?: ReactNode;
};

export function EmptyState({ title, description, icon, actions }: EmptyStateProps) {
  return (
    <div className={styles.wrap}>
      <GlassSurface variant="strong" className={styles.inner}>
        <div className={styles.badge} aria-hidden="true">
          {icon ?? (
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 6v12M6 12h12"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
              />
            </svg>
          )}
        </div>
        <h2 className={styles.title}>{title}</h2>
        <p className={styles.text}>{description}</p>
        {actions ? <div className={styles.actions}>{actions}</div> : null}
      </GlassSurface>
    </div>
  );
}
