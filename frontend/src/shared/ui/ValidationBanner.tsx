import styles from "./ValidationBanner.module.css";

type ValidationBannerProps = {
  variant: "error" | "success" | "info";
  title?: string;
  message?: string;
  messages?: string[];
};

export function ValidationBanner({ variant, title, message, messages }: ValidationBannerProps) {
  const variantClass = variant === "error" ? styles.error : variant === "success" ? styles.success : styles.info;
  const list = messages?.filter(Boolean) ?? [];
  return (
    <div className={[styles.wrap, variantClass].join(" ")} role={variant === "error" ? "alert" : "status"}>
      {title ? <p className={styles.title}>{title}</p> : null}
      {message ? <p className={styles.text}>{message}</p> : null}
      {list.length ? (
        <ul className={styles.list}>
          {list.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
