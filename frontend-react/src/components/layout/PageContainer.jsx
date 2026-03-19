import "./PageContainer.css";

export function PageContainer({ children, narrow = false }) {
  const cls = ["page-container", narrow && "page-container--narrow"].filter(Boolean).join(" ");
  return <main className={cls}>{children}</main>;
}
