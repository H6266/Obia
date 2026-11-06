export type StaffAccount = {
  id: string;
  identity_id: string;
  email: string;
  full_name: string;
  role: string;
  status: string;
  mfa_enabled: boolean;
  created_at: string;
  permissions: string[];
};

export type DashboardMetrics = {
  start: string;
  end: string;
  total_orders: number;
  successful_orders: number;
  pending_orders: number;
  failed_orders: number;
  sample_orders: number;
  active_customers: number;
  requested_order_value: string;
  revenue: string | null;
  net_revenue: string | null;
  gross_profit: string | null;
  available_inventory_units: number | null;
  reserved_inventory_units: number | null;
  delivered_inventory_units: number | null;
  daily_orders: { date: string; orders: number; requested_value: number }[];
  orders_by_network: { network: string; orders: number }[];
  orders_by_status: { status: string; orders: number }[];
  data_availability: Record<string, string>;
};

export type CatalogueNetwork = {
  id: string;
  name: string;
  short_name: string;
  is_active: boolean;
};

export type CatalogueBundle = {
  id: string;
  network_id: string;
  name: string;
  size_gb: string;
  amount: string;
  currency: string;
  is_sample: boolean;
  is_available: boolean;
  category: string;
  validity_days: number | null;
  updated_at: string;
};

export type CatalogueRevision = {
  id: string;
  bundle_id: string;
  actor_email: string;
  previous_value: Record<string, unknown>;
  new_value: Record<string, unknown>;
  reason: string;
  created_at: string;
};

export type AdminOrder = {
  reference: string;
  customer_name: string | null;
  customer_phone: string;
  recipient_phone: string;
  network_id: string;
  network: string;
  bundle_id: string;
  bundle: string;
  amount: string;
  currency: string;
  order_status: string;
  payment_status: string;
  fulfillment_status: string;
  supplier: string | null;
  supplier_reference: string | null;
  agent: string | null;
  created_at: string;
  updated_at: string;
  is_sample: boolean;
};

export type OrderDetail = AdminOrder & {
  failure_reason: string | null;
  timeline: {
    event_type: string;
    previous_status: string | null;
    new_status: string | null;
    actor_type: string;
    actor_label: string;
    reason: string | null;
    details: Record<string, unknown> | null;
    created_at: string;
  }[];
  notes: { id: string; order_reference: string; author_email: string; note: string; created_at: string }[];
  escalations: {
    id: string;
    created_by_email: string;
    reason: string;
    status: string;
    created_at: string;
  }[];
};

export type Customer = {
  id: string;
  full_name: string;
  phone: string;
  phone_verified: boolean;
  account_status: string;
  created_at: string;
  order_count: number;
};

export type CustomerDetail = Customer & {
  orders: AdminOrder[];
  support_records: { id: string; order_reference: string; author_email: string; note: string; created_at: string }[];
};

export type AuditRecord = {
  id: string;
  actor_email: string;
  action: string;
  resource_type: string;
  resource_id: string;
  previous_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  reason: string | null;
  request_id: string;
  created_at: string;
};

export type Page<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
};

export type Invitation = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  expires_at: string;
  accepted_at?: string | null;
  created_at: string;
  invitation_token?: string;
};
