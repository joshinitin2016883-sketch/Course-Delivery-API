"""Render calls /health to check the service is up. It must answer without touching the database:
otherwise every check would wake Neon, which suspends after 5 idle minutes, and a cold database could
fail a check and get the service restarted. See Decision 23."""


def test_health_answers_ok_without_touching_the_database(client, recorded_sql):
    with recorded_sql() as statements:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert statements == []
