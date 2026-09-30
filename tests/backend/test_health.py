def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["service"] in ("backend", "DZ Biometric Platform")


def test_openapi_available(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert "paths" in r.json()