"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { isInProgress, listInvoices } from "@/lib/api";
import { StatusBadge } from "./status-badge";

export function InvoiceTable() {
  const { data, isPending, isError, error } = useQuery({
    queryKey: ["invoices"],
    queryFn: listInvoices,
    // Poll only while something is still being processed.
    refetchInterval: (query) =>
      query.state.data?.items.some((invoice) => isInProgress(invoice.status))
        ? 2000
        : false,
  });

  if (isPending) return <p className="text-sm text-muted">Loading invoices…</p>;
  if (isError)
    return (
      <p className="text-sm text-red-500">
        Could not load invoices: {error.message}. Is the API running?
      </p>
    );
  if (data.items.length === 0)
    return <p className="text-sm text-muted">No invoices yet. Upload one to get started.</p>;

  return (
    <div className="overflow-x-auto rounded-lg border border-line">
      <table className="w-full text-left text-sm">
        <thead className="bg-surface text-xs uppercase tracking-wide text-muted">
          <tr>
            <th className="px-4 py-3 font-medium">File</th>
            <th className="px-4 py-3 font-medium">Vendor</th>
            <th className="px-4 py-3 font-medium">Invoice #</th>
            <th className="px-4 py-3 font-medium">Date</th>
            <th className="px-4 py-3 text-right font-medium">Total</th>
            <th className="px-4 py-3 font-medium">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {data.items.map((invoice) => (
            <tr key={invoice.id} className="hover:bg-surface">
              <td className="max-w-56 truncate px-4 py-3">
                <Link href={`/invoices/${invoice.id}`} className="text-accent hover:underline">
                  {invoice.original_filename}
                </Link>
              </td>
              <td className="px-4 py-3">{invoice.vendor_name ?? "—"}</td>
              <td className="px-4 py-3 font-mono text-xs">{invoice.invoice_number ?? "—"}</td>
              <td className="px-4 py-3">{invoice.issue_date ?? "—"}</td>
              <td className="px-4 py-3 text-right tabular-nums">{invoice.total_amount ?? "—"}</td>
              <td className="px-4 py-3">
                <StatusBadge status={invoice.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
