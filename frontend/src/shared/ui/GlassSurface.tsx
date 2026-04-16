import type { HTMLAttributes, ReactNode } from "react";

import styles from "./GlassSurface.module.css";

type GlassSurfaceProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  variant?: "default" | "strong";
  /** Доп. глубина / свечение (hero, важные карточки) */
  elevated?: boolean;
};

export function GlassSurface({ children, className, variant = "default", elevated = false, ...rest }: GlassSurfaceProps) {
  const cls = [
    styles.root,
    variant === "strong" ? styles.strong : "",
    elevated ? styles.elevated : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}
