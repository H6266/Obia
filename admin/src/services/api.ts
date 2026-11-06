import type {
  AdminOrder,
  AuditRecord,
  CatalogueBundle,
  CatalogueNetwork,
  CatalogueRevision,
  Customer,
  CustomerDetail,
  DashboardMetrics,
  Invitation,
  OrderDetail,
  Page,
  StaffAccount,
} from "../types";

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "/api/v1/admin").replace(/\/+$/, "");
let csrfToken = "";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (init?.method && init.method.toUpperCase() !== "GET" && csrfToken) {
    headers.set("X-CSRF-Token", csrfToken);
  }
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
  const text = await response.text();
  let payload: unknown;
  try {
    payload = text ? JSON.parse(text) : undefined;
  } catch {
    if (response.ok) throw new Error("The API returned an invalid response.");
  }
  if (!response.ok) {
    const message =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? String(payload.detail)
        : `The API request failed (${response.status}).`;
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  if (payload === undefined) throw new Error("The API returned an empty response.");
  return payload as T;
}

async function refreshCsrf(): Promise<void> {
  const result = await request<{ csrf_token: string }>("/auth/csrf");
  csrfToken = result.csrf_token;
}

export const api = {
  async me(): Promise<StaffAccount> {
    return request("/auth/me");
  },
  async login(payload: { email: string; password: string; totp_code: string }): Promise<StaffAccount> {
    const staff = await request<StaffAccount>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    await refreshCsrf();
    return staff;
  },
  async logout(): Promise<void> {
    await request<void>("/auth/logout", { method: "POST" });
    csrfToken = "";
  },
  async restore(): Promise<StaffAccount> {
    const staff = await request<StaffAccount>("/auth/me");
    await refreshCsrf();
    return staff;
  },
  dashboard(period: string, startDate?: string, endDate?: string): Promise<DashboardMetrics> {
    const params = new URLSearchParams({ period });
    if (period === "custom" && startDate) params.set("start_date", startDate);
    if (period === "custom" && endDate) params.set("end_date", endDate);
    return request(`/dashboard?${params.toString()}`);
  },
  orders(params: URLSearchParams): Promise<Page<AdminOrder>> {
    return request(`/orders?${params.toString()}`);
  },
  order(reference: string): Promise<OrderDetail> {
    return request(`/orders/${encodeURIComponent(reference)}`);
  },
  addOrderNote(reference: string, note: string): Promise<void> {
    return request(`/orders/${encodeURIComponent(reference)}/notes`, {
      method: "POST",
      body: JSON.stringify({ note }),
    });
  },
  escalateOrder(reference: string, reason: string): Promise<void> {
    return request(`/orders/${encodeURIComponent(reference)}/escalations`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  },
  customers(params: URLSearchParams): Promise<Page<Customer>> {
    return request(`/customers?${params.toString()}`);
  },
  customer(id: string): Promise<CustomerDetail> {
    return request(`/customers/${encodeURIComponent(id)}`);
  },
  setCustomerStatus(id: string, status: "active" | "suspended", reason: string): Promise<Customer> {
    return request(`/customers/${encodeURIComponent(id)}/status`, {
      method: "POST",
      body: JSON.stringify({ status, reason }),
    });
  },
  audit(page: number): Promise<AuditRecord[]> {
    return request(`/audit?page=${page}&page_size=50`);
  },
  roles(): Promise<{ role: string; permissions: string[] }[]> {
    return request("/staff/roles");
  },
  staff(): Promise<StaffAccount[]> {
    return request("/staff");
  },
  invitations(): Promise<Invitation[]> {
    return request("/staff/invitations");
  },
  invite(payload: { email: string; full_name: string; role: string }): Promise<Invitation> {
    return request("/staff/invitations", { method: "POST", body: JSON.stringify(payload) });
  },
  catalogueNetworks(): Promise<CatalogueNetwork[]> {
    return request("/catalogue/networks");
  },
  catalogueBundles(params: URLSearchParams): Promise<Page<CatalogueBundle>> {
    return request(`/catalogue/bundles?${params.toString()}`);
  },
  updateBundle(id: string, payload: Record<string, unknown>): Promise<CatalogueBundle> {
    return request(`/catalogue/bundles/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  bundleHistory(id: string): Promise<CatalogueRevision[]> {
    return request(`/catalogue/bundles/${encodeURIComponent(id)}/history`);
  },
  updateNetworkStatus(
    id: string,
    is_active: boolean,
    reason: string,
  ): Promise<CatalogueNetwork> {
    return request(`/catalogue/networks/${encodeURIComponent(id)}/status`, {
      method: "PATCH",
      body: JSON.stringify({ is_active, reason }),
    });
  },
  acceptInvitation(token: string, password: string): Promise<{
    enrollment_token: string;
    totp_secret: string;
    issuer: string;
    account_name: string;
  }> {
    return request("/auth/accept-invitation", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    });
  },
  confirmMfa(enrollment_token: string, totp_code: string): Promise<StaffAccount> {
    return request("/auth/confirm-enrollment", {
      method: "POST",
      body: JSON.stringify({ enrollment_token, totp_code }),
    });
  },
};

export function isUnauthenticated(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}
