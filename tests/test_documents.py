from io import BytesIO

from pypdf import PdfWriter


def _minimal_pdf() -> bytes:
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    buf = BytesIO()
    w.write(buf)
    return buf.getvalue()


def test_stats_summary_no_auth(client):
    """Operational route intentionally without principal dependency."""
    r = client.get("/api/v1/documents/stats/summary")
    assert r.status_code == 200
    data = r.json()
    assert "document_count" in data
    assert "tenant_count" in data


def test_upload_forbidden_for_viewer(client, auth_viewer):
    files = {"file": ("a.pdf", _minimal_pdf(), "application/pdf")}
    data = {"logical_name": "Report"}
    r = client.post("/api/v1/documents", headers=auth_viewer, files=files, data=data)
    assert r.status_code == 403


def test_upload_happy_path(client, auth_editor):
    files = {"file": ("a.pdf", _minimal_pdf(), "application/pdf")}
    data = {"logical_name": "Q1 Report"}
    r = client.post("/api/v1/documents", headers=auth_editor, files=files, data=data)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["logical_name"] == "Q1 Report"
    assert body["version"] == 1
    assert body["malware_scan_status"] == "clean"
    assert "sha256" in body["metadata"]


def test_upload_rejects_bad_extension(client, auth_editor):
    files = {"file": ("x.txt", b"hello", "text/plain")}
    data = {"logical_name": "nope"}
    r = client.post("/api/v1/documents", headers=auth_editor, files=files, data=data)
    assert r.status_code == 415


def test_upload_rejects_oversized(client, auth_editor, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "10")
    from app.core.config import get_settings

    get_settings.cache_clear()
    files = {"file": ("big.pdf", b"x" * 20, "application/pdf")}
    data = {"logical_name": "big"}
    r = client.post("/api/v1/documents", headers=auth_editor, files=files, data=data)
    assert r.status_code == 413
    get_settings.cache_clear()


def test_versioning_second_upload(client, auth_editor):
    files1 = {"file": ("v1.pdf", _minimal_pdf(), "application/pdf")}
    r1 = client.post(
        "/api/v1/documents",
        headers=auth_editor,
        files=files1,
        data={"logical_name": "Same"},
    )
    doc_id = r1.json()["document_id"]
    files2 = {"file": ("v2.pdf", _minimal_pdf(), "application/pdf")}
    r2 = client.post(
        "/api/v1/documents",
        headers=auth_editor,
        files=files2,
        data={"logical_name": "Same", "document_id": doc_id},
    )
    assert r2.status_code == 201
    assert r2.json()["version"] == 2


def test_get_document_cross_tenant_404(client, auth_editor):
    files = {"file": ("a.pdf", _minimal_pdf(), "application/pdf")}
    r = client.post(
        "/api/v1/documents",
        headers=auth_editor,
        files=files,
        data={"logical_name": "Secret"},
    )
    doc_id = r.json()["document_id"]
    other = {
        "X-User-Id": "u2",
        "X-Tenant-Id": "tenant-b",
        "X-User-Roles": "viewer",
    }
    r2 = client.get(f"/api/v1/documents/{doc_id}", headers=other)
    assert r2.status_code == 404


def test_search_metadata(client, auth_editor, auth_viewer):
    files = {"file": ("findme.pdf", _minimal_pdf(), "application/pdf")}
    client.post(
        "/api/v1/documents",
        headers=auth_editor,
        files=files,
        data={"logical_name": "findme-report"},
    )
    r = client.get("/api/v1/documents/search", headers=auth_viewer, params={"q": "findme"})
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_presigned_url_stub(client, auth_editor):
    files = {"file": ("a.pdf", _minimal_pdf(), "application/pdf")}
    up = client.post(
        "/api/v1/documents",
        headers=auth_editor,
        files=files,
        data={"logical_name": "DL"},
    )
    doc_id = up.json()["document_id"]
    r = client.get(
        f"/api/v1/documents/{doc_id}/download-url",
        headers=auth_editor,
    )
    assert r.status_code == 200
    assert "presign" in r.json()["url"]
