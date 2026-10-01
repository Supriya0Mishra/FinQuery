const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type InvoiceStatus =
  | "queued"
  | "processing"
  | "needs_review"
  | "approved"
  | "failed";

export interface InvoiceSummary {
  id: string;
  original_filename: string;
  status: InvoiceStatus;
  error: string | null;
  vendor_name: string | null;
  invoice_number: string | null;
  issue_date: string | null;
  total_amount: string | null;
  created_at: string;
  updated_at: string;
}

export interface LineItem {
  id: string;
  position: number;
  description: string;
  quantity: string | null;
  unit_price: string | null;
  amount: string | null;
}

export interface InvoiceDetail extends InvoiceSummary {
  size_bytes: number;
  page_count: number | null;
  document_type: string | null;
  customer_name: string | null;
  due_date: string | null;
  currency: string | null;
  subtotal: string | null;
  tax_amount: string | null;
  payment_terms: string | null;
  text_truncated: boolean;
  line_items: LineItem[];
}

export interface InvoiceList {
  items: InvoiceSummary[];
  total: number;
}

export interface UploadResult {
  filename: string;
  outcome: "accepted" | "duplicate" | "rejected";
  detail: string | null;
  invoice: InvoiceSummary | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}/api${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return response.json();
}

export const isInProgress = (status: InvoiceStatus) =>
  status === "queued" || status === "processing";

export const listInvoices = () => request<InvoiceList>("/invoices");

export const getInvoice = (id: string) =>
  request<InvoiceDetail>(`/invoices/${id}`);

export const invoiceFileUrl = (id: string) =>
  `${API_URL}/api/invoices/${id}/file`;

export const retryInvoice = (id: string) =>
  request<InvoiceSummary>(`/invoices/${id}/retry`, { method: "POST" });

export function uploadInvoices(files: File[]) {
  const body = new FormData();
  for (const file of files) body.append("files", file);
  return request<UploadResult[]>("/invoices", { method: "POST", body });
}
