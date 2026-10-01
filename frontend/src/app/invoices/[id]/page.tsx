import Link from "next/link";
import { InvoiceDetail } from "@/components/invoice-detail";

export default async function InvoicePage(props: PageProps<"/invoices/[id]">) {
  const { id } = await props.params;
  return (
    <div className="space-y-4">
      <Link href="/" className="text-sm text-muted hover:underline">
        ← Back to inbox
      </Link>
      <InvoiceDetail id={id} />
    </div>
  );
}
