from tests.conftest import ADMIN_ID, CUSTOMER_ID, bearer


# --- /api/auth/me -----------------------------------------------------------

def test_me_requires_a_token(client, fake_auth):
    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_me_rejects_an_invalid_token(client, fake_auth):
    response = client.get("/api/auth/me", headers=bearer("not-a-real-token"))

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired access token"}


def test_me_rejects_a_non_bearer_scheme(client, fake_auth):
    response = client.get(
        "/api/auth/me", headers={"Authorization": "Basic customer-token"}
    )

    assert response.status_code == 401


def test_me_returns_the_callers_profile(client, fake_auth):
    response = client.get("/api/auth/me", headers=bearer("customer-token"))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == CUSTOMER_ID
    assert body["role"] == "customer"
    assert body["email"] == "customer@example.com"
    # The profile is read with a client scoped to the caller's own token, so
    # row level security applies.
    assert fake_auth.user_client_tokens == ["customer-token"]


def test_me_profile_lookup_failure_returns_500(client, fake_auth):
    fake_auth.profile_error = RuntimeError("database unavailable")

    response = client.get("/api/auth/me", headers=bearer("customer-token"))

    assert response.status_code == 500
    assert response.json() == {"detail": "Unable to retrieve profile"}


# --- /api/auth/admin-test ---------------------------------------------------

def test_admin_endpoint_requires_a_token(client, fake_auth):
    response = client.get("/api/auth/admin-test")

    assert response.status_code == 401


def test_admin_endpoint_rejects_customers(client, fake_auth):
    response = client.get("/api/auth/admin-test", headers=bearer("customer-token"))

    assert response.status_code == 403
    assert response.json() == {"detail": "Administrator access required"}


def test_admin_endpoint_allows_admins(client, fake_auth):
    response = client.get("/api/auth/admin-test", headers=bearer("admin-token"))

    assert response.status_code == 200
    assert response.json() == {"message": "Admin access granted", "user_id": ADMIN_ID}


def test_admin_endpoint_role_lookup_failure_returns_503(client, fake_auth):
    fake_auth.profile_error = RuntimeError("database unavailable")

    response = client.get("/api/auth/admin-test", headers=bearer("admin-token"))

    assert response.status_code == 503
    assert response.json() == {"detail": "Unable to verify account role"}
