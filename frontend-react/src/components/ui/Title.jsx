import "./Title.css";

export function Title({ children, level = 1, subtitle = null }) {
  const Tag = `h${level}`;
  return (
    <div className="title-block">
      <Tag className={`title title--h${level}`}>{children}</Tag>
      {subtitle && <p className="title__subtitle">{subtitle}</p>}
    </div>
  );
}
