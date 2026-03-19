import "./Button.css";

export function Button({ children, variant = "primary", disabled = false, onClick, type = "button", fullWidth = false }) {
  const cls = ["btn", `btn--${variant}`, fullWidth && "btn--full"].filter(Boolean).join(" ");
  return (
    <button className={cls} disabled={disabled} onClick={onClick} type={type}>
      {children}
    </button>
  );
}
