import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../auth/AuthContext";

const links = [
  { to: "/", label: "Overview", permission: "dashboard.read" },
  { to: "/orders", label: "Orders", permission: "orders.read" },
  { to: "/customers", label: "Customers", permission: "customers.read" },
  { to: "/staff", label: "Staff access", permission: "staff.manage" },
  { to: "/audit", label: "Audit log", permission: "audit.read" },
];

export function AdminLayout() {
  const { staff, logout } = useAuth();
  const navigate = useNavigate();
  const [logoutError, setLogoutError] = useState("");

  async function handleLogout() {
    setLogoutError("");
    try {
      await logout();
      navigate("/login", { replace: true });
    } catch (error) {
      setLogoutError(error instanceof Error ? error.message : "Could not sign out.");
    }
  }

  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <Link className="admin-brand" to="/">falaaa<span>.</span><small>OPERATIONS</small></Link>
        <nav aria-label="Operations navigation">
          {links.filter((link) => staff?.permissions.includes(link.permission)).map((link) => (
            <NavLink key={link.to} end={link.to === "/"} to={link.to}>{link.label}</NavLink>
          ))}
        </nav>
        <div className="admin-sidebar__user">
          <strong>{staff?.full_name}</strong>
          <span>{staff?.role.replaceAll("_", " ")}</span>
          <button type="button" onClick={handleLogout}>Sign out</button>
          {logoutError && <p role="alert">{logoutError}</p>}
        </div>
      </aside>
      <main className="admin-main">
        <Outlet />
      </main>
    </div>
  );
}
