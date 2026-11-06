import type { NetworkId } from "../data/networks";

export type Bundle = {
  id: string;
  network_id: NetworkId;
  name: string;
  size_gb: string;
  amount: string;
  currency: string;
  is_sample: boolean;
  is_available: boolean;
};

export type PurchaseOrder = {
  reference: string;
  amount: string;
  currency: string;
  network_id: NetworkId;
  network: string;
  bundle_id: string;
  bundle: string;
  customer_phone: string;
  status: string;
  created_at: string;
  is_sample: boolean;
};

export type CustomerAccount = {
  id: string;
  full_name: string;
  phone: string;
  phone_verified: boolean;
  account_status: string;
  role: string;
  created_at: string;
};

export type ApiHealth = {
  status: string;
  database: string;
};

export type RegisterRequest = {
  full_name: string;
  phone: string;
  password: string;
};

export type LoginRequest = {
  phone: string;
  password: string;
};

export type CreateOrderRequest = {
  phone: string;
  network_id: NetworkId;
  bundle_id: string;
};

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/+$/, "");
let csrfToken = "";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fieldErrors: Record<string, string> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function responseMessage(payload: unknown, status: number): string {
  if (typeof payload === "object" && payload !== null && "detail" in payload) {
    const detail = payload.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (typeof item === "object" && item !== null && "msg" in item) {
            return String(item.msg);
          }
          return "Invalid request.";
        })
        .join(" ");
    }
  }
  return `The API request failed (${status}).`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (
    init?.method &&
    !["GET", "HEAD", "OPTIONS"].includes(init.method.toUpperCase()) &&
    csrfToken
  ) {
    headers.set("X-CSRF-Token", csrfToken);
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
  const responseText = await response.text();
  let payload: unknown;
  try {
    payload = responseText ? JSON.parse(responseText) : undefined;
  } catch {
    if (response.ok) throw new Error("The API returned an invalid response.");
  }

  if (!response.ok) {
    const errors: Record<string, string> = {};
    if (typeof payload === "object" && payload !== null && "detail" in payload) {
      const detail = payload.detail;
      if (Array.isArray(detail)) {
        for (const item of detail) {
          if (
            typeof item === "object" &&
            item !== null &&
            "loc" in item &&
            "msg" in item &&
            Array.isArray(item.loc)
          ) {
            const field = item.loc.at(-1);
            if (typeof field === "string") errors[field] = String(item.msg);
          }
        }
      }
    }
    throw new ApiError(responseMessage(payload, response.status), response.status, errors);
  }
  if (response.status === 204) return undefined as T;
  if (payload === undefined) throw new Error("The API returned an empty response.");
  return payload as T;
}

export function getBundles(networkId: NetworkId): Promise<Bundle[]> {
  return request(`/networks/${encodeURIComponent(networkId)}/bundles`);
}

export function getApiHealth(): Promise<ApiHealth> {
  return request("/health");
}

export function createOrder(order: CreateOrderRequest): Promise<PurchaseOrder> {
  return request("/orders", { method: "POST", body: JSON.stringify(order) });
}

export function getOrder(reference: string): Promise<PurchaseOrder> {
  return request(`/orders/${encodeURIComponent(reference.trim())}`);
}

export function getCustomer(): Promise<CustomerAccount> {
  return request("/auth/me");
}

export async function registerCustomer(
  payload: RegisterRequest,
): Promise<CustomerAccount> {
  const customer = await request<CustomerAccount>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  await refreshCsrfToken();
  return customer;
}

export async function loginCustomer(
  payload: LoginRequest,
): Promise<CustomerAccount> {
  const customer = await request<CustomerAccount>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  await refreshCsrfToken();
  return customer;
}

export async function logoutCustomer(): Promise<void> {
  await request<void>("/auth/logout", { method: "POST" });
  csrfToken = "";
}

export async function refreshCsrfToken(): Promise<void> {
  const result = await request<{ csrf_token: string }>("/auth/csrf");
  csrfToken = result.csrf_token;
}

export function getCustomerOrders(): Promise<PurchaseOrder[]> {
  return request("/customers/me/orders");
}

export function resendPhoneVerification(): Promise<void> {
  return request("/auth/resend-verification", { method: "POST" });
}

export function verifyPhone(code: string): Promise<void> {
  return request("/auth/verify-phone", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

export function requestPasswordRecovery(phone: string): Promise<void> {
  return request("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ phone }),
  });
}
