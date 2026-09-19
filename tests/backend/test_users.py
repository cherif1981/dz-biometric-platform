def test_register_success(client):
    r = client.post(
        "/api/users/register",
        json={"email": "new@dz.dz", "password": "secret123"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "new@dz.dz"
    assert "id" in body
    assert "hashed_password" not in body


def test_register_duplicate(client, test_user):
    r = client.post(
        "/api/users/register",
        json={"email": test_user.email, "password": "secret123"},
    )
    assert r.status_code == 400


def test_register_invalid_email(client):
    r = client.post(
        "/api/users/register",
        json={"email": "not-an-email", "password": "secret123"},
    )
    assert r.status_code == 422