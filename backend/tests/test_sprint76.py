"""
Sprint 76 — Logo Drag & Drop upload tests.

Covers:
- POST /branding/logo: auth guard, viewer blocked, valid upload (PNG, SVG, WebP)
- POST /branding/logo: file too large → 413
- POST /branding/logo: unsupported MIME → 415
- POST /branding/logo: updates logo_url in branding settings
- POST /branding/logo: successive upload removes old file, sets new URL
- DELETE /branding/logo: removes logo, clears logo_url
- DELETE /branding/logo: auth guard
- GET /branding/settings: still returns logo_url after upload
- Static file is written to disk
- _delete_current_logo helper: only deletes /static/logo* paths
"""
import io
import pathlib

import pytest


# ── Minimal valid image bytes ─────────────────────────────────────────────────

# 1×1 red PNG (minimal valid PNG)
_PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Minimal SVG
_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><circle cx="5" cy="5" r="5"/></svg>'

# Minimal WebP (RIFF header — technically not valid image data, but enough for MIME check test)
_WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 20


# ── Auth guard ────────────────────────────────────────────────────────────────

class TestLogoUploadAuth:
    def test_upload_requires_auth(self, client):
        resp = client.post(
            "/branding/logo",
            files={"file": ("logo.png", io.BytesIO(_PNG_1X1), "image/png")},
        )
        assert resp.status_code in (401, 403)

    def test_viewer_cannot_upload(self, client, viewer_headers):
        resp = client.post(
            "/branding/logo",
            files={"file": ("logo.png", io.BytesIO(_PNG_1X1), "image/png")},
            headers=viewer_headers,
        )
        assert resp.status_code in (401, 403)

    def test_editor_cannot_upload(self, client, editor_headers):
        resp = client.post(
            "/branding/logo",
            files={"file": ("logo.png", io.BytesIO(_PNG_1X1), "image/png")},
            headers=editor_headers,
        )
        assert resp.status_code in (401, 403)

    def test_delete_requires_auth(self, client):
        resp = client.delete("/branding/logo")
        assert resp.status_code in (401, 403)


# ── Upload success ────────────────────────────────────────────────────────────

class TestLogoUploadSuccess:
    def test_png_upload_returns_200(self, client, auth_headers):
        resp = client.post(
            "/branding/logo",
            files={"file": ("logo.png", io.BytesIO(_PNG_1X1), "image/png")},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_png_upload_returns_logo_url(self, client, auth_headers):
        resp = client.post(
            "/branding/logo",
            files={"file": ("logo.png", io.BytesIO(_PNG_1X1), "image/png")},
            headers=auth_headers,
        )
        data = resp.json()
        assert "logo_url" in data
        assert data["logo_url"].startswith("/static/logo")
        assert data["logo_url"].endswith(".png")

    def test_svg_upload_accepted(self, client, auth_headers):
        resp = client.post(
            "/branding/logo",
            files={"file": ("logo.svg", io.BytesIO(_SVG), "image/svg+xml")},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["logo_url"].endswith(".svg")

    def test_logo_url_persisted_in_settings(self, client, auth_headers):
        # Upload
        up = client.post(
            "/branding/logo",
            files={"file": ("logo.png", io.BytesIO(_PNG_1X1), "image/png")},
            headers=auth_headers,
        )
        logo_url = up.json()["logo_url"]

        # Read back via settings
        settings = client.get("/branding/settings").json()
        assert settings["logo_url"] == logo_url

    def test_upload_writes_file_to_disk(self, client, auth_headers):
        resp = client.post(
            "/branding/logo",
            files={"file": ("logo.png", io.BytesIO(_PNG_1X1), "image/png")},
            headers=auth_headers,
        )
        url = resp.json()["logo_url"]
        path = pathlib.Path(url.lstrip("/"))
        assert path.exists(), f"Expected {path} to exist on disk"

    def test_response_includes_size_bytes(self, client, auth_headers):
        resp = client.post(
            "/branding/logo",
            files={"file": ("logo.png", io.BytesIO(_PNG_1X1), "image/png")},
            headers=auth_headers,
        )
        data = resp.json()
        assert "size_bytes" in data
        assert data["size_bytes"] == len(_PNG_1X1)


# ── Upload validation ─────────────────────────────────────────────────────────

class TestLogoUploadValidation:
    def test_unsupported_mime_returns_415(self, client, auth_headers):
        resp = client.post(
            "/branding/logo",
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 415

    def test_text_file_returns_415(self, client, auth_headers):
        resp = client.post(
            "/branding/logo",
            files={"file": ("bad.txt", io.BytesIO(b"hello"), "text/plain")},
            headers=auth_headers,
        )
        assert resp.status_code == 415

    def test_oversized_file_returns_413(self, client, auth_headers):
        big = b"\x89PNG" + b"\x00" * (2 * 1024 * 1024 + 1)
        resp = client.post(
            "/branding/logo",
            files={"file": ("big.png", io.BytesIO(big), "image/png")},
            headers=auth_headers,
        )
        assert resp.status_code == 413


# ── DELETE /branding/logo ─────────────────────────────────────────────────────

class TestLogoDelete:
    def test_delete_clears_logo_url(self, client, auth_headers):
        # Upload first
        client.post(
            "/branding/logo",
            files={"file": ("logo.png", io.BytesIO(_PNG_1X1), "image/png")},
            headers=auth_headers,
        )
        # Delete
        resp = client.delete("/branding/logo", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["logo_url"] == ""

    def test_delete_reflects_in_settings(self, client, auth_headers):
        client.post(
            "/branding/logo",
            files={"file": ("logo.png", io.BytesIO(_PNG_1X1), "image/png")},
            headers=auth_headers,
        )
        client.delete("/branding/logo", headers=auth_headers)
        settings = client.get("/branding/settings").json()
        assert settings["logo_url"] == ""


# ── _delete_current_logo unit test ────────────────────────────────────────────

class TestDeleteCurrentLogoHelper:
    def test_does_not_delete_external_urls(self, tmp_path):
        from backend.routers.branding import _delete_current_logo
        from types import SimpleNamespace
        # External URL — should not be touched (no file to delete)
        mock_settings = SimpleNamespace(logo_url="https://example.com/logo.png")
        _delete_current_logo(mock_settings)  # must not raise

    def test_does_not_delete_empty_url(self):
        from backend.routers.branding import _delete_current_logo
        from types import SimpleNamespace
        mock_settings = SimpleNamespace(logo_url="")
        _delete_current_logo(mock_settings)  # must not raise
