import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "./auth/AuthContext";
import { AdminLayout } from "./components/AdminLayout";
import { AuditPage } from "./pages/AuditPage";
import { CataloguePage } from "./pages/CataloguePage";
import { CustomersPage } from "./pages/CustomersPage";
import { DashboardPage } from "./pages/DashboardPage";
import { InvitePage } from "./pages/InvitePage";
import { LoginPage } from "./pages/LoginPage";
import { OrdersPage } from "./pages/OrdersPage";
import { StaffPage } from "./pages/StaffPage";

function Protected({ children }: { children: ReactNode }) {
  const { staff, loading } = useAuth();
  const location = useLocation();
  if (loading) return <main className="auth-page"><p role="status">Checking staff session…</p></main>;
  return staff ? children : <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
}

function PermissionRoute({ permission, children }: { permission: string; children: ReactNode }) {
  const { staff } = useAuth();
  return staff?.permissions.includes(permission)
    ? children
    : <main className="page"><h1>Access denied</h1><p>Your staff role does not grant this permission.</p></main>;
}

function GuestOnly({ children }: { children: ReactNode }) {
  const { staff, loading } = useAuth();
  if (loading) return <main className="auth-page"><p role="status">Checking staff session…</p></main>;
  return staff ? <Navigate to="/" replace /> : children;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<GuestOnly><LoginPage /></GuestOnly>} />
      <Route path="/invite" element={<InvitePage />} />
      <Route path="/" element={<Protected><AdminLayout /></Protected>}>
        <Route index element={<PermissionRoute permission="dashboard.read"><DashboardPage /></PermissionRoute>} />
        <Route path="orders" element={<PermissionRoute permission="orders.read"><OrdersPage /></PermissionRoute>} />
        <Route path="customers" element={<PermissionRoute permission="customers.read"><CustomersPage /></PermissionRoute>} />
        <Route path="catalogue" element={<PermissionRoute permission="catalogue.read"><CataloguePage /></PermissionRoute>} />
        <Route path="staff" element={<PermissionRoute permission="staff.manage"><StaffPage /></PermissionRoute>} />
        <Route path="audit" element={<PermissionRoute permission="audit.read"><AuditPage /></PermissionRoute>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
