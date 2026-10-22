import type { InvoiceStatus } from "@/lib/api";

const STYLES: Record<InvoiceStatus, { label: string; className: string }> = {
  queued: { label: "Queued", className: "bg-gray-500/15 text-gray-500" },
  processing: {
    label: "Processing",
    className: "bg-blue-500/15 text-blue-500 animate-pulse",
  },
  needs_review: {
    label: "Needs review",
    className: "bg-amber-500/15 text-amber-600",
  },
  approved: { label: "Approved", className: "bg-green-500/15 text-green-600" },
  failed: { label: "Failed", className: "bg-red-500/15 text-red-500" },
};

export function StatusBadge({ status }: { status: InvoiceStatus }) {
  const { label, className } = STYLES[status];
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}
    >
      {label}
    </span>
  );
}
