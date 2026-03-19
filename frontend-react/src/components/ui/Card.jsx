import "./Card.css";

export function Card({ children, variant = "default", onClick, className = "" }) {
  const cls = ["card", `card--${variant}`, onClick && "card--clickable", className].filter(Boolean).join(" ");
  return (
    <div className={cls} onClick={onClick} role={onClick ? "button" : undefined} tabIndex={onClick ? 0 : undefined}>
      {children}
    </div>
  );
}
