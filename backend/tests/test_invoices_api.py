import uuid

from app.models import Invoice, InvoiceStatus

PDF = b"%PDF-1.4\nfake body"


def upload(client, *files):
    return client.post(
        "/api/invoices",
        files=[("files", (name, data, "application/pdf")) for name, data in files],
    )


def test_upload_stores_file_and_enqueues(client, storage, enqueued):
    response = upload(client, ("a.pdf", PDF))

    assert response.status_code == 202
    [result] = response.json()
    assert result["outcome"] == "accepted"
    assert result["invoice"]["status"] == "queued"

    invoice_id = result["invoice"]["id"]
    assert storage.objects[f"invoices/{invoice_id}.pdf"] == PDF
    assert enqueued == [uuid.UUID(invoice_id)]


def test_same_file_twice_is_a_duplicate_and_not_reprocessed(client, enqueued):
    first = upload(client, ("a.pdf", PDF)).json()[0]
    second = upload(client, ("renamed.pdf", PDF)).json()[0]

    assert second["outcome"] == "duplicate"
    assert second["invoice"]["id"] == first["invoice"]["id"]
    assert len(enqueued) == 1


def test_bad_file_is_rejected_without_failing_the_batch(client, enqueued):
    results = upload(client, ("notes.pdf", b"just text"), ("ok.pdf", PDF)).json()

    assert [r["outcome"] for r in results] == ["rejected", "accepted"]
    assert results[0]["detail"] == "Not a PDF file"
    assert len(enqueued) == 1


def test_list_filters_by_status(client):
    upload(client, ("a.pdf", PDF), ("b.pdf", PDF + b"2"))

    assert client.get("/api/invoices").json()["total"] == 2
    assert client.get("/api/invoices", params={"status": "queued"}).json()["total"] == 2
    assert client.get("/api/invoices", params={"status": "approved"}).json()["total"] == 0


def test_detail_file_and_404(client):
    invoice_id = upload(client, ("a.pdf", PDF)).json()[0]["invoice"]["id"]

    detail = client.get(f"/api/invoices/{invoice_id}").json()
    assert detail["line_items"] == []
    assert detail["size_bytes"] == len(PDF)

    file_response = client.get(f"/api/invoices/{invoice_id}/file")
    assert file_response.content == PDF
    assert file_response.headers["content-type"] == "application/pdf"

    assert client.get(f"/api/invoices/{uuid.uuid4()}").status_code == 404


def test_retry_only_allowed_for_failed(client, session_factory, enqueued):
    invoice_id = upload(client, ("a.pdf", PDF)).json()[0]["invoice"]["id"]
    assert client.post(f"/api/invoices/{invoice_id}/retry").status_code == 409

    with session_factory() as db:
        invoice = db.get(Invoice, uuid.UUID(invoice_id))
        invoice.status = InvoiceStatus.FAILED
        invoice.error = "boom"
        db.commit()

    response = client.post(f"/api/invoices/{invoice_id}/retry")
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["error"] is None
    assert len(enqueued) == 2
