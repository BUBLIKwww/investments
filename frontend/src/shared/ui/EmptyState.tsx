import type { ReactNode } from "react";

import { GlassSurface } from "@/shared/ui/GlassSurface";

import styles from "./EmptyState.module.css";

type EmptyStateProps = {
  title: string;
  description: string;
  /** Короткая подпись над заголовком (как section label в iOS) */
  kicker?: string;
  icon?: ReactNode;
  actions?: ReactNode;
};

export function EmptyState({ title, description, kicker, icon, actions }: EmptyStateProps) {
  return (
    <div className={styles.wrap}>
      <GlassSurface variant="strong" elevated className={styles.inner}>
        <div className={styles.orbWrap}>
          <div className={styles.orbGlow} aria-hidden="true" />
          <div className={styles.badge} aria-hidden="true">
            {icon ?? (
              <svg viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 6v12M6 12h12"
                  stroke="currentColor"
                  strokeWidth="1.65"
                  strokeLinecap="round"
                />
              </svg>
            )}
          </div>
        </div>
        {kicker ? <p className={styles.kicker}>{kicker}</p> : null}
        <h2 className={styles.title}>{title}</h2>
        <p className={styles.text}>{description}</p>
        {actions ? <div className={styles.actions}>{actions}</div> : null}
      </GlassSurface>
    </div>
  );
}
