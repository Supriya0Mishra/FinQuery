import { InvoiceTable } from "@/components/invoice-table";
import { UploadDropzone } from "@/components/upload-dropzone";

export default function InboxPage() {
  return (
    <div className="space-y-8">
      <UploadDropzone />
      <section>
        <h2 className="mb-3 font-medium">Invoices</h2>
        <InvoiceTable />
      </section>
    </div>
  );
}
