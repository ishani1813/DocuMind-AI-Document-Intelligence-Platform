"""
Workspace isolation tests.

Save this as: backend/tests/test_workspace_isolation.py
Run with: pytest tests/test_workspace_isolation.py -v

These tests exist to prove (and guard against regressing) the fix in
documents.py: a document scoped to a workspace should be visible to
workspace members and invisible to everyone else, and only the uploader
or a workspace OWNER/ADMIN should be able to delete it.
"""

import io
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.main import app
from app.core.database import get_db

# Reuses the same sqlite test-db wiring as test_api.py — if you run this
# file on its own, make sure app.dependency_overrides[get_db] is already
# set (importing test_api first, or copying its fixtures, works fine).


async def _register_and_login(client: AsyncClient, email: str) -> dict:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": email.split("@")[0],
        "password": "testpass123",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "testpass123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_non_member_cannot_see_workspace_document():
    async with AsyncClient(app=app, base_url="http://test") as client:
        owner_headers = await _register_and_login(client, "owner@example.com")
        outsider_headers = await _register_and_login(client, "outsider@example.com")

        # Owner creates a workspace and uploads a doc into it
        ws_resp = await client.post(
            "/api/v1/workspaces/",
            headers=owner_headers,
            json={"name": "Owner's Workspace"},
        )
        workspace_id = ws_resp.json()["id"]

        upload_resp = await client.post(
            "/api/v1/documents/upload",
            headers=owner_headers,
            data={"workspace_id": workspace_id},
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )
        assert upload_resp.status_code == 201
        document_id = upload_resp.json()["id"]

        # Outsider (not a member) should NOT be able to see it
        list_resp = await client.get(
            "/api/v1/documents/",
            headers=outsider_headers,
            params={"workspace_id": workspace_id},
        )
        assert list_resp.status_code == 403  # not a member at all

        get_resp = await client.get(f"/api/v1/documents/{document_id}", headers=outsider_headers)
        assert get_resp.status_code == 404  # exists, but not visible to a non-member


@pytest.mark.asyncio
async def test_invited_member_can_see_but_not_delete():
    async with AsyncClient(app=app, base_url="http://test") as client:
        owner_headers = await _register_and_login(client, "owner2@example.com")
        member_headers = await _register_and_login(client, "member2@example.com")

        ws_resp = await client.post(
            "/api/v1/workspaces/",
            headers=owner_headers,
            json={"name": "Shared Workspace"},
        )
        workspace_id = ws_resp.json()["id"]

        # Owner invites member2 as a plain MEMBER (not admin/owner)
        invite_resp = await client.post(
            f"/api/v1/workspaces/{workspace_id}/invite",
            headers=owner_headers,
            json={"email": "member2@example.com", "role": "member"},
        )
        assert invite_resp.status_code == 200

        upload_resp = await client.post(
            "/api/v1/documents/upload",
            headers=owner_headers,
            data={"workspace_id": workspace_id},
            files={"file": ("shared.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )
        document_id = upload_resp.json()["id"]

        # Member CAN now see the shared document — this is the fix working
        get_resp = await client.get(f"/api/v1/documents/{document_id}", headers=member_headers)
        assert get_resp.status_code == 200

        # But member CANNOT delete a document they didn't upload
        delete_resp = await client.delete(f"/api/v1/documents/{document_id}", headers=member_headers)
        assert delete_resp.status_code == 403

        # Owner still can
        owner_delete_resp = await client.delete(f"/api/v1/documents/{document_id}", headers=owner_headers)
        assert owner_delete_resp.status_code == 204


@pytest.mark.asyncio
async def test_upload_rejects_unverified_workspace_id():
    async with AsyncClient(app=app, base_url="http://test") as client:
        owner_headers = await _register_and_login(client, "owner3@example.com")
        attacker_headers = await _register_and_login(client, "attacker3@example.com")

        ws_resp = await client.post(
            "/api/v1/workspaces/",
            headers=owner_headers,
            json={"name": "Private Workspace"},
        )
        workspace_id = ws_resp.json()["id"]

        # Attacker (not a member) tries to upload a doc tagged with someone
        # else's workspace_id — this must be rejected, not silently accepted.
        resp = await client.post(
            "/api/v1/documents/upload",
            headers=attacker_headers,
            data={"workspace_id": workspace_id},
            files={"file": ("evil.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )
        assert resp.status_code == 403
