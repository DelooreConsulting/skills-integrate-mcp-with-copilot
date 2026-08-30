from fastapi.testclient import TestClient

from src.app import app

client = TestClient(app)


def test_student_can_register_and_log_in_then_sign_up_for_own_activity():
    register_response = client.post(
        "/auth/register",
        json={
            "email": "alice@mergington.edu",
            "password": "secure-password",
            "name": "Alice Student",
        },
    )

    assert register_response.status_code == 200, register_response.text
    token = register_response.json()["token"]

    login_response = client.post(
        "/auth/login",
        json={"email": "alice@mergington.edu", "password": "secure-password"},
    )

    assert login_response.status_code == 200, login_response.text
    assert login_response.json()["user"]["email"] == "alice@mergington.edu"
    assert login_response.json()["token"]

    signup_response = client.post(
        "/activities/Chess%20Club/signup",
        headers={"Authorization": f"Bearer {login_response.json()['token']}"},
    )

    assert signup_response.status_code == 200, signup_response.text
    assert "alice@mergington.edu" in client.get("/activities").json()["Chess Club"]["participants"]


def test_student_cannot_sign_up_for_another_student_without_permission():
    register_response = client.post(
        "/auth/register",
        json={
            "email": "bob@mergington.edu",
            "password": "another-password",
            "name": "Bob Student",
        },
    )

    assert register_response.status_code == 200, register_response.text
    token = register_response.json()["token"]

    signup_response = client.post(
        "/activities/Programming%20Class/signup?email=carol@mergington.edu",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert signup_response.status_code == 403, signup_response.text
    detail = signup_response.json()["detail"].lower()
    assert "own" in detail or "manage" in detail


def test_unauthenticated_users_cannot_manage_activities():
    response = client.post("/activities/Chess%20Club/signup?email=dan@mergington.edu")

    assert response.status_code == 401, response.text
