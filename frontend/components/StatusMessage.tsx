import styles from "./ui.module.css";

type StatusMessageProps = {
  type: "success" | "error" | "info";
  message: string;
  title?: string;
};

export function StatusMessage({ type, message, title }: StatusMessageProps) {
  return (
    <div
      className={`${styles.statusMessage} ${styles[`status-${type}`]}`}
      role={type === "error" ? "alert" : "status"}
      aria-live={type === "error" ? "assertive" : "polite"}
    >
      {title ? <strong>{title}</strong> : null}
      <p>{message}</p>
    </div>
  );
}
