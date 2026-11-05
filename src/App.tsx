import { useEffect, useRef, useState } from "react";
import {
  BrowserRouter,
  Link,
  NavLink,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { AgentPage } from "./pages/AgentPage";
import { BusinessPage } from "./pages/BusinessPage";
import { HomePage } from "./pages/HomePage";
import { InfoPage } from "./pages/InfoPage";
import { OrdersPage } from "./pages/OrdersPage";
import { Icon } from "./components/Ui";

const navigation = [
  { to: "/", label: "Home", end: true },
  { to: "/orders", label: "Track order" },
  { to: "/agent", label: "For agents" },
  { to: "/business", label: "Business" },
];

function Brand({ footer = false }: { footer?: boolean }) {
  return (
    <Link aria-label="Falaaa home" className={`brand${footer ? " brand--footer" : ""}`} to="/">
      <span className="brand-symbol">f</span>
      <span>falaaa<span className="brand-period">.</span></span>
    </Link>
  );
}

function SignInDialog({ onClose }: { onClose: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    dialog.showModal();
    return () => dialog.close();
  }, []);

  return (
    <dialog
      aria-labelledby="sign-in-title"
      className="account-dialog"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === dialogRef.current) onClose();
      }}
      ref={dialogRef}
    >
      <div className="account-dialog__content">
        <button aria-label="Close dialog" className="icon-button account-dialog__close" onClick={onClose} type="button">
          <Icon name="close" size={19} />
        </button>
        <span className="account-dialog__mark"><Icon name="phone" size={21} /></span>
        <span className="eyebrow">WELCOME TO FALAAA</span>
        <h2 id="sign-in-title">Your account is coming soon.</h2>
        <p>Secure phone verification will be available when Falaaa account services are connected.</p>
        <div className="account-dialog__note">
          <Icon name="lock" size={15} />
          We will never ask for your mobile money PIN.
        </div>
        <button className="button button--primary button--wide" onClick={onClose} type="button">Got it</button>
      </div>
    </dialog>
  );
}

function SiteHeader({ onSignIn }: { onSignIn: () => void }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="site-header">
      <div className="site-header__inner">
        <Brand />
        <nav aria-label="Main navigation" className={`main-nav${menuOpen ? " main-nav--open" : ""}`}>
          {navigation.map((item) => (
            <NavLink
              end={"end" in item ? item.end : false}
              key={item.to}
              onClick={() => setMenuOpen(false)}
              to={item.to}
            >
              {item.label}
            </NavLink>
          ))}
          <button className="main-nav__mobile-signin" onClick={onSignIn} type="button">Sign in</button>
        </nav>
        <div className="site-header__actions">
          <button className="signin-button" onClick={onSignIn} type="button">Sign in</button>
          <Link className="button button--primary header-buy" to="/#purchase">
            Buy data
            <Icon name="arrow-up-right" size={15} />
          </Link>
        </div>
        <button
          aria-expanded={menuOpen}
          aria-label={menuOpen ? "Close navigation" : "Open navigation"}
          className="icon-button menu-toggle"
          onClick={() => setMenuOpen((open) => !open)}
          type="button"
        >
          <Icon name={menuOpen ? "close" : "menu"} size={21} />
        </button>
      </div>
    </header>
  );
}

function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer__main">
        <div className="site-footer__brand">
          <Brand footer />
          <p>Making it easier to stay connected, wherever the day takes you.</p>
          <span className="footer-country"><span className="ghana-dot" /> Ghana</span>
        </div>
        <div className="site-footer__column">
          <strong>Explore</strong>
          <Link to="/">Buy data</Link>
          <Link to="/orders">Track an order</Link>
          <Link to="/agent">Become an agent</Link>
        </div>
        <div className="site-footer__column">
          <strong>For business</strong>
          <Link to="/business">Business workspace</Link>
          <a href="mailto:business@falaaa.example">Partner enquiries</a>
          <a href="mailto:support@falaaa.example">Contact support</a>
        </div>
        <div className="site-footer__column">
          <strong>Good to know</strong>
          <Link to="/privacy">Privacy</Link>
          <Link to="/terms">Terms of use</Link>
          <span className="footer-placeholder">Contact details pending launch</span>
        </div>
      </div>
      <div className="site-footer__bottom">
        <span>© {new Date().getFullYear()} Falaaa. Ghana.</span>
        <span>Mobile money PINs are never requested or stored by Falaaa.</span>
        <span className="footer-status"><span /> Product preview</span>
      </div>
    </footer>
  );
}

function ScrollToTop() {
  const { pathname, hash } = useLocation();

  useEffect(() => {
    if (hash) {
      requestAnimationFrame(() => {
        document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: "smooth" });
      });
    } else {
      window.scrollTo({ top: 0, behavior: "instant" });
    }
    const titles: Record<string, string> = {
      "/": "Falaaa — Data that keeps Ghana moving",
      "/orders": "Your orders — Falaaa",
      "/agent": "Agent workbench — Falaaa",
      "/business": "Business workspace — Falaaa",
      "/privacy": "Privacy — Falaaa",
      "/terms": "Terms of use — Falaaa",
    };
    document.title = titles[pathname] ?? "Falaaa";
  }, [pathname, hash]);

  return null;
}

function AppRoutes() {
  const [signInOpen, setSignInOpen] = useState(false);

  return (
    <div className="app-shell">
      <ScrollToTop />
      <a className="skip-link" href="#main-content">Skip to content</a>
      <SiteHeader onSignIn={() => setSignInOpen(true)} />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/orders" element={<OrdersPage />} />
        <Route path="/agent" element={<AgentPage />} />
        <Route path="/business" element={<BusinessPage />} />
        <Route path="/privacy" element={<InfoPage />} />
        <Route path="/terms" element={<InfoPage />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
      <SiteFooter />
      {signInOpen && <SignInDialog onClose={() => setSignInOpen(false)} />}
    </div>
  );
}

function NotFound() {
  return (
    <main className="workspace-page" id="main-content" tabIndex={-1}>
      <div className="workspace-container">
        <div className="not-found">
          <span className="eyebrow">404 · PAGE NOT FOUND</span>
          <h1>Looks like you took a wrong turn.</h1>
          <p>The page you’re looking for isn’t here, but your next connection could be.</p>
          <Link className="button button--primary" to="/">Back to Falaaa home <Icon name="arrow-right" size={16} /></Link>
        </div>
      </div>
    </main>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
