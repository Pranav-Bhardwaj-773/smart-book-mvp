def auth(client):
    res = client.post(
        "/auth/login",
        json={"email": "reader@smartbook.local", "password": "Reader123!"},
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_third_rental_rejected(client):
    h = auth(client)
    assert client.post("/rentals", json={"book_id": 1}, headers=h).status_code == 201
    assert client.post("/rentals", json={"book_id": 2}, headers=h).status_code == 201
    third = client.post("/rentals", json={"book_id": 4}, headers=h)
    assert third.status_code == 409
    assert "two active rentals" in third.json()["detail"]


def test_duplicate_same_book(client):
    h = auth(client)
    assert client.post("/rentals", json={"book_id": 1}, headers=h).status_code == 201
    dup = client.post("/rentals", json={"book_id": 1}, headers=h)
    assert dup.status_code == 409
    assert "active rental for this book" in dup.json()["detail"]


def test_return_frees_slot(client):
    h = auth(client)
    first = client.post("/rentals", json={"book_id": 1}, headers=h)
    assert first.status_code == 201
    client.post("/rentals", json={"book_id": 2}, headers=h)
    rid = first.json()["id"]
    assert client.post(f"/rentals/{rid}/return", headers=h).status_code == 200
    again = client.post("/rentals", json={"book_id": 4}, headers=h)
    assert again.status_code == 201


def test_guest_cannot_rent(client):
    res = client.post("/rentals", json={"book_id": 1})
    assert res.status_code == 401