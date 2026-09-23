def exercise_id(client, headers, name="Bench press"):
    exercises = client.get("/api/exercises", headers=headers).json()
    return next(e["id"] for e in exercises if e["name"] == name)


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_register_login_me(client):
    body = {"email": "Sam@Example.com", "display_name": "Sam", "password": "supersecret"}
    r = client.post("/api/auth/register", json=body)
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "sam@example.com"

    assert client.post("/api/auth/register", json=body).status_code == 409

    r = client.post("/api/auth/login", json={"email": "sam@example.com", "password": "supersecret"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["display_name"] == "Sam"


def test_bad_login_and_short_password(client):
    r = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "whatever1"})
    assert r.status_code == 401
    r = client.post(
        "/api/auth/register", json={"email": "a@example.com", "display_name": "A", "password": "short"}
    )
    assert r.status_code == 422


def test_requires_auth(client):
    assert client.get("/api/lifts").status_code == 401
    assert client.get("/api/exercises", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_log_lifts_and_progress(client, make_user):
    h = make_user()
    bench = exercise_id(client, h)
    for day, weight, reps in [("2026-01-05", 80, 5), ("2026-01-12", 85, 5), ("2026-01-19", 90, 3)]:
        r = client.post(
            "/api/lifts",
            headers=h,
            json={"exercise_id": bench, "weight_kg": weight, "reps": reps, "sets": 3, "performed_on": day},
        )
        assert r.status_code == 201, r.text

    lifts = client.get("/api/lifts", headers=h).json()
    assert [l["weight_kg"] for l in lifts] == [90, 85, 80]  # newest first

    p = client.get(f"/api/lifts/progress?exercise_id={bench}", headers=h).json()
    assert [pt["top_weight_kg"] for pt in p["points"]] == [80, 85, 90]
    assert p["best_weight_kg"] == 90
    assert p["best_weight_date"] == "2026-01-19"


def test_lifts_are_private_per_user(client, make_user):
    alice, bob = make_user("Alice"), make_user("Bob")
    squat = exercise_id(client, alice, "Back squat")
    r = client.post("/api/lifts", headers=alice, json={"exercise_id": squat, "weight_kg": 100, "reps": 5})
    lift_id = r.json()["id"]

    assert client.get("/api/lifts", headers=bob).json() == []
    assert client.delete(f"/api/lifts/{lift_id}", headers=bob).status_code == 404
    assert client.delete(f"/api/lifts/{lift_id}", headers=alice).status_code == 204
    assert client.get("/api/lifts", headers=alice).json() == []


def test_custom_exercises(client, make_user):
    alice, bob = make_user("Alice"), make_user("Bob")
    r = client.post("/api/exercises", headers=alice, json={"name": "  Farmer   walk "})
    assert r.status_code == 201 and r.json()["name"] == "Farmer walk"
    assert client.post("/api/exercises", headers=alice, json={"name": "farmer walk"}).status_code == 409
    assert client.post("/api/exercises", headers=alice, json={"name": "Bench press"}).status_code == 409

    assert "Farmer walk" in [e["name"] for e in client.get("/api/exercises", headers=alice).json()]
    assert "Farmer walk" not in [e["name"] for e in client.get("/api/exercises", headers=bob).json()]

    # Bob can't log against Alice's private exercise
    r = client.post("/api/lifts", headers=bob, json={"exercise_id": r.json()["id"], "weight_kg": 40, "reps": 1})
    assert r.status_code == 404
