"""
Sprint 58 — User avatar upload/delete tests.
  POST   /users/me/avatar  — any auth
  DELETE /users/me/avatar  — any auth
"""
import pytest

# Minimal valid 200×200 JPEG data URL (tiny placeholder — real avatars are larger)
_FAKE_AVATAR = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAARC"


class TestAvatarUpload:
    def test_requires_auth(self, client):
        r = client.post("/users/me/avatar", json={"avatar_url": _FAKE_AVATAR})
        assert r.status_code == 401

    def test_delete_requires_auth(self, client):
        r = client.delete("/users/me/avatar")
        assert r.status_code == 401

    def test_upload_valid_data_url(self, client, auth_headers):
        r = client.post(
            "/users/me/avatar",
            json={"avatar_url": _FAKE_AVATAR},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["avatar_url"] == _FAKE_AVATAR

    def test_upload_non_image_url_rejected(self, client, auth_headers):
        r = client.post(
            "/users/me/avatar",
            json={"avatar_url": "data:text/plain;base64,SGVsbG8="},
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_upload_plain_string_rejected(self, client, auth_headers):
        r = client.post(
            "/users/me/avatar",
            json={"avatar_url": "https://example.com/avatar.jpg"},
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_avatar_returned_in_users_me(self, client, auth_headers):
        # Upload
        client.post("/users/me/avatar", json={"avatar_url": _FAKE_AVATAR}, headers=auth_headers)
        # Fetch profile
        r = client.get("/users/me", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["avatar_url"] == _FAKE_AVATAR

    def test_delete_avatar(self, client, auth_headers):
        # First upload
        client.post("/users/me/avatar", json={"avatar_url": _FAKE_AVATAR}, headers=auth_headers)
        # Then delete
        r = client.delete("/users/me/avatar", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["avatar_url"] is None

    def test_avatar_returned_in_list_users(self, client, auth_headers):
        # Upload avatar for testadmin
        client.post("/users/me/avatar", json={"avatar_url": _FAKE_AVATAR}, headers=auth_headers)
        # List users as super_admin
        r = client.get("/users", headers=auth_headers)
        assert r.status_code == 200
        users = r.json()
        testadmin = next((u for u in users if u["username"] == "testadmin"), None)
        assert testadmin is not None
        assert testadmin["avatar_url"] == _FAKE_AVATAR

    def test_viewer_can_upload_own_avatar(self, client, viewer_headers):
        r = client.post(
            "/users/me/avatar",
            json={"avatar_url": _FAKE_AVATAR},
            headers=viewer_headers,
        )
        assert r.status_code == 200

    def test_viewer_can_delete_own_avatar(self, client, viewer_headers):
        r = client.delete("/users/me/avatar", headers=viewer_headers)
        assert r.status_code == 200
