"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getInvoice, invoiceFileUrl, isInProgress, retryInvoice } from "@/lib/api";
import { StatusBadge } from "./status-badge";

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-0.5">{value ?? "—"}</dd>
    </div>
  );
}

export function InvoiceDetail({ id }: { id: string }) {
  const queryClient = useQueryClient();
  const {
    data: invoice,
    isPending,
    isError,
    error,
  } = useQuery({
    queryKey: ["invoices", id],
    queryFn: () => getInvoice(id),
    refetchInterval: (query) =>
      query.state.data && isInProgress(query.state.data.status) ? 2000 : false,
  });

  const retry = useMutation({
    mutationFn: () => retryInvoice(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["invoices"] }),
  });

  if (isPending) return <p className="text-sm text-muted">Loading…</p>;
  if (isError) return <p className="text-sm text-red-500">{error.message}</p>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold">{invoice.original_filename}</h1>
        <StatusBadge status={invoice.status} />
        <a
          href={invoiceFileUrl(id)}
          target="_blank"
          rel="noreferrer"
          className="ml-auto text-sm text-accent hover:underline"
        >
          Open original PDF
        </a>
      </div>

      {invoice.status === "failed" && (
        <div className="rounded-lg border border-red-500/40 bg-red-500/5 p-4 text-sm">
          <p className="text-red-500">{invoice.error}</p>
          <button
            type="button"
            onClick={() => retry.mutate()}
            disabled={retry.isPending}
            className="mt-3 rounded-md border border-line px-3 py-1.5 font-medium hover:bg-surface disabled:opacity-60"
          >
            {retry.isPending ? "Retrying…" : "Retry"}
          </button>
        </div>
      )}

      {isInProgress(invoice.status) && (
        <p className="text-sm text-muted">
          Extraction is running in the background. This page updates automatically.
        </p>
      )}

      {invoice.text_truncated && (
        <p className="rounded-lg border border-amber-500/40 bg-amber-500/5 p-4 text-sm text-amber-600">
          This document was too long to read in full. Fields near the end may be missing.
        </p>
      )}

      <dl className="grid grid-cols-2 gap-x-6 gap-y-4 rounded-lg border border-line p-5 text-sm sm:grid-cols-3">
        <Field label="Vendor" value={invoice.vendor_name} />
        <Field label="Customer" value={invoice.customer_name} />
        <Field label="Document type" value={invoice.document_type} />
        <Field label="Invoice #" value={invoice.invoice_number} />
        <Field label="Issue date" value={invoice.issue_date} />
        <Field label="Due date" value={invoice.due_date} />
        <Field label="Currency" value={invoice.currency} />
        <Field label="Payment terms" value={invoice.payment_terms} />
        <Field label="Pages" value={invoice.page_count?.toString() ?? null} />
        <Field label="Subtotal" value={invoice.subtotal} />
        <Field label="Tax" value={invoice.tax_amount} />
        <Field label="Total" value={invoice.total_amount} />
      </dl>

      <section>
        <h2 className="mb-2 font-medium">Line items</h2>
        {invoice.line_items.length === 0 ? (
          <p className="text-sm text-muted">No line items extracted.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-line">
            <table className="w-full text-left text-sm">
              <thead className="bg-surface text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-4 py-3 font-medium">Description</th>
                  <th className="px-4 py-3 text-right font-medium">Qty</th>
                  <th className="px-4 py-3 text-right font-medium">Unit price</th>
                  <th className="px-4 py-3 text-right font-medium">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {invoice.line_items.map((item) => (
                  <tr key={item.id}>
                    <td className="px-4 py-3">{item.description}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{item.quantity ?? "—"}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{item.unit_price ?? "—"}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{item.amount ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
