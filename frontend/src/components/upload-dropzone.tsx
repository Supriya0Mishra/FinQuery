"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { uploadInvoices } from "@/lib/api";

export function UploadDropzone() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const queryClient = useQueryClient();

  const upload = useMutation({
    mutationFn: uploadInvoices,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["invoices"] }),
  });

  function send(fileList: FileList | null) {
    const files = Array.from(fileList ?? []);
    if (files.length > 0) upload.mutate(files);
  }

  const notAccepted = upload.data?.filter((r) => r.outcome !== "accepted") ?? [];

  return (
    <div>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          send(event.dataTransfer.files);
        }}
        disabled={upload.isPending}
        className={`w-full rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${
          dragging ? "border-accent bg-accent/5" : "border-line bg-surface"
        } ${upload.isPending ? "opacity-60" : "cursor-pointer hover:border-accent"}`}
      >
        <p className="font-medium">
          {upload.isPending ? "Uploading…" : "Drop invoice PDFs here, or click to browse"}
        </p>
        <p className="mt-1 text-sm text-muted">
          Multiple files supported. Each one is processed in the background.
        </p>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        multiple
        hidden
        onChange={(event) => {
          send(event.target.files);
          event.target.value = "";
        }}
      />

      {upload.isError && (
        <p className="mt-3 text-sm text-red-500">{upload.error.message}</p>
      )}
      {notAccepted.length > 0 && (
        <ul className="mt-3 space-y-1 text-sm">
          {notAccepted.map((result) => (
            <li
              key={result.filename}
              className={result.outcome === "rejected" ? "text-red-500" : "text-amber-600"}
            >
              {result.filename}: {result.detail}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
