import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { DataState, Icon, NoticeBanner, PageIntro } from "../components/Ui";
import {
  getCustomerOrders,
  resendPhoneVerification,
  type PurchaseOrder,
} from "../lib/api";

export function DashboardPage() {
  const { customer, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [ordersLoading, setOrdersLoading] = useState(true);
  const [ordersError, setOrdersError] = useState("");
  const [verificationMessage, setVerificationMessage] = useState("");
  const [verificationError, setVerificationError] = useState("");
  const [verificationLoading, setVerificationLoading] = useState(false);
  const [logoutError, setLogoutError] = useState("");

  useEffect(() => {
    let active = true;
    getCustomerOrders()
      .then((result) => {
        if (active) setOrders(result);
      })
      .catch((error: unknown) => {
        if (active) {
          setOrdersError(
            error instanceof Error ? error.message : "Could not load your order history.",
          );
        }
      })
      .finally(() => {
        if (active) setOrdersLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleResendVerification() {
    setVerificationLoading(true);
    setVerificationMessage("");
    setVerificationError("");
    try {
      await resendPhoneVerification();
      setVerificationMessage("A verification message was requested.");
    } catch (error) {
      setVerificationError(
        error instanceof Error ? error.message : "Phone verification is unavailable.",
      );
    } finally {
      setVerificationLoading(false);
    }
  }

  async function handleLogout() {
    setLogoutError("");
    try {
      await logout();
      navigate("/", { replace: true });
    } catch (error) {
      setLogoutError(error instanceof Error ? error.message : "Could not sign out.");
    }
  }

  return (
    <main className="workspace-page" id="main-content" tabIndex={-1}>
      <div className="workspace-container">
        <PageIntro
          eyebrow="MY FALAAA ACCOUNT"
          title={`Hello, ${customer?.full_name ?? "customer"}.`}
          description="Manage your account details and review purchase requests linked to your account."
          actions={
            <button className="button button--outline" onClick={handleLogout} type="button">
              <Icon name="close" size={16} />
              Sign out
            </button>
          }
        />

        {location.state?.welcome && (
          <NoticeBanner title="Your account is ready">
            Your account is active, but your phone number is not verified. No SMS has been sent because a verification provider is not configured.
          </NoticeBanner>
        )}

        <section className="account-details-card" aria-labelledby="account-details-title">
          <div className="account-details-card__heading">
            <div>
              <span className="eyebrow">ACCOUNT DETAILS</span>
              <h2 id="account-details-title">Your profile</h2>
            </div>
            <span className={`account-verification${customer?.phone_verified ? " is-verified" : ""}`}>
              {customer?.phone_verified ? "Phone verified" : "Phone unverified"}
            </span>
          </div>
          <dl>
            <div><dt>Full name</dt><dd>{customer?.full_name}</dd></div>
            <div><dt>Phone number</dt><dd>{customer?.phone}</dd></div>
            <div><dt>Account status</dt><dd>{customer?.account_status}</dd></div>
            <div><dt>Member since</dt><dd>{customer ? new Date(customer.created_at).toLocaleDateString() : "—"}</dd></div>
          </dl>
          {!customer?.phone_verified && (
            <div className="account-verification-action">
              <button
                className="button button--outline"
                disabled={verificationLoading}
                onClick={handleResendVerification}
                type="button"
              >
                {verificationLoading ? "Checking…" : "Request phone verification"}
              </button>
              <span>SMS verification is unavailable until a provider is connected.</span>
            </div>
          )}
          {verificationError && <p className="account-error" role="alert">{verificationError}</p>}
          {verificationMessage && <p className="account-success" role="status">{verificationMessage}</p>}
          {logoutError && <p className="account-error" role="alert">{logoutError}</p>}
        </section>

        <section className="history-section dashboard-orders" aria-labelledby="dashboard-orders-title">
          <div className="section-heading section-heading--compact">
            <div>
              <span className="eyebrow">PURCHASE ACTIVITY</span>
              <h2 id="dashboard-orders-title">Your recent orders</h2>
            </div>
            <Link className="button button--primary" to="/#purchase">
              Buy data <Icon name="arrow-right" size={16} />
            </Link>
          </div>
          {ordersError && <p className="account-error" role="alert">{ordersError}</p>}
          {ordersLoading ? (
            <div className="account-loading" role="status">Loading your orders…</div>
          ) : orders.length ? (
            <div className="history-table-wrap">
              <table className="history-table">
                <thead>
                  <tr>
                    <th scope="col">Reference</th>
                    <th scope="col">Network / bundle</th>
                    <th scope="col">Amount</th>
                    <th scope="col">Status</th>
                    <th scope="col">Date</th>
                    <th scope="col">Tracking</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((order) => (
                    <tr key={order.reference}>
                      <td>{order.reference}</td>
                      <td>{order.network} · {order.bundle}</td>
                      <td>GHS {Number(order.amount).toFixed(2)}</td>
                      <td>{order.status.replaceAll("_", " ")}</td>
                      <td>{new Date(order.created_at).toLocaleDateString()}</td>
                      <td><Link to={`/orders?reference=${encodeURIComponent(order.reference)}`}>Track</Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <DataState icon="receipt" title="No orders yet">
              Purchase requests linked to your account will appear here.
              <Link className="button button--primary" to="/#purchase">Buy data</Link>
            </DataState>
          )}
        </section>
      </div>
    </main>
  );
}
