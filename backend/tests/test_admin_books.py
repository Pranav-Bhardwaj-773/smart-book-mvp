def admin_auth(client):
    res = client.post(
        "/auth/login",
        json={"email": "admin@smartbook.local", "password": "Admin123!"},
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_admin_can_add_book(client):
    headers = admin_auth(client)
    res = client.post(
        "/admin/books",
        headers=headers,
        json={
            "isbn": "9780000099991",
            "title": "New Book",
            "authors": "Tester",
            "description": "A description",
            "total_copies": 2,
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["title"] == "New Book"
    assert body["available_copies"] == 2
    assert body["cover_url"]
