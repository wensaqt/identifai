import "./Alert.css";

export function Alert({ children, variant = "error" }) {
  return <div className={`alert alert--${variant}`}>{children}</div>;
}
