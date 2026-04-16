import type { HTMLAttributes, ReactNode } from "react";

import styles from "./GlassSurface.module.css";

type GlassSurfaceProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  variant?: "default" | "strong";
};

export function GlassSurface({ children, className, variant = "default", ...rest }: GlassSurfaceProps) {
  const cls = [styles.root, variant === "strong" ? styles.strong : "", className].filter(Boolean).join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}
