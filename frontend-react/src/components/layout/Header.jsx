import { Link } from "react-router-dom";
import "./Header.css";

export function Header() {
  return (
    <header className="header">
      <Link to="/" className="header__brand">
        <span className="header__logo">IdentifAI</span>
      </Link>
      <nav className="header__nav">
        <Link to="/" className="header__link">Accueil</Link>
        <Link to="/history" className="header__link">Historique</Link>
      </nav>
    </header>
  );
}
