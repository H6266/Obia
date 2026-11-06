import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  BrowserRouter,
  Link,
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { AgentPage } from "./pages/AgentPage";
import { BusinessPage } from "./pages/BusinessPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { HomePage } from "./pages/HomePage";
import { InfoPage } from "./pages/InfoPage";
import { LoginPage } from "./pages/LoginPage";
import { OrdersPage } from "./pages/OrdersPage";
import { SignupPage } from "./pages/SignupPage";
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

function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const { customer, loading, logout } = useAuth();

  async function handleLogout() {
    setLogoutError("");
    try {
      await logout();
    } catch (error) {
      setLogoutError(error instanceof Error ? error.message : "Could not sign out.");
    }
  }

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
          {customer ? (
            <>
              <Link className="main-nav__mobile-signin" onClick={() => setMenuOpen(false)} to="/dashboard">My account</Link>
              <button className="main-nav__mobile-signin" onClick={handleLogout} type="button">Sign out</button>
            </>
          ) : !loading && (
            <>
              <Link className="main-nav__mobile-signin" onClick={() => setMenuOpen(false)} to="/login">Sign in</Link>
              <Link className="main-nav__mobile-signin" onClick={() => setMenuOpen(false)} to="/signup">Create an account</Link>
            </>
          )}
        </nav>
        <div className="site-header__actions">
          {customer ? (
            <>
              <Link className="signin-button" to="/dashboard">My account</Link>
              <button className="signin-button" onClick={handleLogout} type="button">Sign out</button>
            </>
          ) : !loading && (
            <>
              <Link className="signin-button" to="/login">Sign in</Link>
              <Link className="signin-button" to="/signup">Sign up</Link>
            </>
          )}
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
      {logoutError && <p className="header-account-error" role="alert">{logoutError}</p>}
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
          <Link to="/dashboard">My account</Link>
          <Link to="/agent">Become an agent</Link>
        </div>
        <div className="site-footer__column">
          <strong>For business</strong>
          <Link to="/business">Business workspace</Link>
          <span>Partner enquiries (details pending)</span>
          <span>Support contact (details pending)</span>
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
      "/dashboard": "My Falaaa account",
      "/signup": "Create an account — Falaaa",
      "/login": "Sign in — Falaaa",
      "/forgot-password": "Recover account — Falaaa",
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
  return (
    <div className="app-shell">
      <ScrollToTop />
      <a className="skip-link" href="#main-content">Skip to content</a>
      <SiteHeader />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/orders" element={<OrdersPage />} />
        <Route path="/signup" element={<GuestOnly><SignupPage /></GuestOnly>} />
        <Route path="/login" element={<GuestOnly><LoginPage /></GuestOnly>} />
        <Route path="/forgot-password" element={<GuestOnly><ForgotPasswordPage /></GuestOnly>} />
        <Route path="/dashboard" element={<RequireCustomer><DashboardPage /></RequireCustomer>} />
        <Route path="/agent" element={<AgentPage />} />
        <Route path="/business" element={<BusinessPage />} />
        <Route path="/privacy" element={<InfoPage />} />
        <Route path="/terms" element={<InfoPage />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
      <SiteFooter />
    </div>
  );
}

function RequireCustomer({ children }: { children: ReactNode }) {
  const { customer, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return <main className="account-page" id="main-content"><p role="status">Checking your account…</p></main>;
  }
  if (!customer) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return children;
}

function GuestOnly({ children }: { children: ReactNode }) {
  const { customer, loading } = useAuth();
  if (loading) {
    return <main className="account-page" id="main-content"><p role="status">Checking your account…</p></main>;
  }
  return customer ? <Navigate to="/dashboard" replace /> : children;
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
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
