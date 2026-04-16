import type { ButtonHTMLAttributes, ReactNode } from "react";

import styles from "./Button.module.css";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
  size?: "md" | "sm";
  children: ReactNode;
};

export function Button({ variant = "secondary", size = "md", className, ...props }: ButtonProps) {
  const variantClass = variant === "primary" ? styles.primary : variant === "ghost" ? styles.ghost : "";
  const classes = [styles.button, variantClass, size === "sm" ? styles.sm : "", className]
    .filter(Boolean)
    .join(" ");
  return <button type="button" className={classes} {...props} />;
}
