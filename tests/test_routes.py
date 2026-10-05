from app import create_app


def test_routes():
    app = create_app()
    client = app.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/api/symptoms/").status_code == 200
    assert client.get("/api/history/").status_code == 200
