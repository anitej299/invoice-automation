export type Item = {
  description: string;
  quantity: string;
  unit_price: string;
  tax: string;
  amount: string;
};
export type Invoice = {
  id: number;
  invoice_number: string | null;
  vendor_name: string | null;
  vendor_email: string | null;
  vendor_address: string | null;
  customer_name: string | null;
  customer_address: string | null;
  invoice_date: string | null;
  due_date: string | null;
  purchase_order_number: string | null;
  currency: string | null;
  subtotal: string | null;
  tax: string | null;
  discount: string | null;
  total: string | null;
  payment_terms: string | null;
  status: string;
  risk_level: string;
  risk_reasons: string[];
  validation_errors: string[];
  confidence: Record<string, number>;
  warnings: string[];
  google_drive_url: string | null;
  source_filename: string | null;
  extracted_text: string | null;
  items: Item[];
  created_at: string;
  paid_at: string | null;
};
export type Page<T> = {
  items: T[];
  total: number;
  page?: number;
  page_size?: number;
};
export type Audit = {
  id: number;
  invoice_id: number;
  action: string;
  description: string;
  performed_by: string;
  created_at: string;
};
export type Vendor = {
  id: number;
  name: string;
  email: string | null;
  address: string | null;
};
export type Stats = {
  total_invoices: number;
  pending: number;
  due_soon: number;
  overdue: number;
  paid: number;
  high_risk: number;
  amounts_by_currency: Record<string, { total: string; outstanding: string }>;
};
export type Series = { name: string; value: number }[];
export type Charts = {
  by_status: Series;
  by_risk: Series;
  monthly_value: Series;
  vendor_spending: Series;
  processing_trend: Series;
  overdue_trend: Series;
};
