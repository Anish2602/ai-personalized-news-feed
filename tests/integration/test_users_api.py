from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.asyncio


async def test_create_and_get_user(client):
    resp = await client.post("/api/v1/users", json={"email": "a@example.com", "name": "Ada"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@example.com"
    user_id = body["id"]

    got = await client.get(f"/api/v1/users/{user_id}")
    assert got.status_code == 200
    assert got.json()["name"] == "Ada"


async def test_duplicate_email_conflicts(client):
    payload = {"email": "dup@example.com", "name": "First"}
    assert (await client.post("/api/v1/users", json=payload)).status_code == 201
    resp = await client.post("/api/v1/users", json={"email": "dup@example.com", "name": "Second"})
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


async def test_invalid_email_is_422(client):
    resp = await client.post("/api/v1/users", json={"email": "not-an-email", "name": "X"})
    assert resp.status_code == 422


async def test_get_missing_user_is_404(client):
    resp = await client.get(f"/api/v1/users/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


async def test_assign_and_list_interests(client):
    user_id = (
        await client.post("/api/v1/users", json={"email": "i@example.com", "name": "I"})
    ).json()["id"]

    resp = await client.post(
        f"/api/v1/users/{user_id}/interests",
        json={"items": [{"name": "Cloud", "weight": 2.0}, {"name": "AI", "weight": 1.5}]},
    )
    assert resp.status_code == 201
    assert {i["name"] for i in resp.json()} == {"Cloud", "AI"}

    # Re-assigning updates the weight rather than duplicating.
    resp = await client.post(
        f"/api/v1/users/{user_id}/interests",
        json={"items": [{"name": "Cloud", "weight": 5.0}]},
    )
    listed = (await client.get(f"/api/v1/users/{user_id}/interests")).json()
    weights = {i["name"]: i["weight"] for i in listed}
    assert weights == {"Cloud": 5.0, "AI": 1.5}


async def test_remove_interest(client):
    user_id = (
        await client.post("/api/v1/users", json={"email": "d@example.com", "name": "D"})
    ).json()["id"]
    await client.post(
        f"/api/v1/users/{user_id}/interests",
        json={"items": [{"name": "Cloud", "weight": 2.0}, {"name": "AI", "weight": 1.5}]},
    )

    resp = await client.delete(f"/api/v1/users/{user_id}/interests/Cloud")
    assert resp.status_code == 204

    listed = (await client.get(f"/api/v1/users/{user_id}/interests")).json()
    assert {i["name"] for i in listed} == {"AI"}


async def test_remove_missing_interest_is_404(client):
    user_id = (
        await client.post("/api/v1/users", json={"email": "e@example.com", "name": "E"})
    ).json()["id"]
    resp = await client.delete(f"/api/v1/users/{user_id}/interests/Cloud")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"
