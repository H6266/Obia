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

export type CreateOrderRequest = {
  phone: string;
  network_id: NetworkId;
  bundle_id: string;
};

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/+$/, "");

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

  const response = await fetch(`${apiBaseUrl}${path}`, { ...init, headers });
  const responseText = await response.text();
  let payload: unknown;
  try {
    payload = responseText ? JSON.parse(responseText) : undefined;
  } catch {
    if (response.ok) throw new Error("The API returned an invalid response.");
  }

  if (!response.ok) throw new Error(responseMessage(payload, response.status));
  if (payload === undefined) throw new Error("The API returned an empty response.");
  return payload as T;
}

export function getBundles(networkId: NetworkId): Promise<Bundle[]> {
  return request(`/networks/${encodeURIComponent(networkId)}/bundles`);
}

export function createOrder(order: CreateOrderRequest): Promise<PurchaseOrder> {
  return request("/orders", { method: "POST", body: JSON.stringify(order) });
}

export function getOrder(reference: string): Promise<PurchaseOrder> {
  return request(`/orders/${encodeURIComponent(reference.trim())}`);
}
