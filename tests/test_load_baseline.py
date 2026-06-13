from perf.load_baseline import apply_login_env_overrides


def test_apply_login_env_overrides_replaces_credentials(monkeypatch):
    monkeypatch.setenv("LOAD_LOGIN_EMAIL", "bench@example.local")
    monkeypatch.setenv("LOAD_LOGIN_PASSWORD", "bench-password")

    updated = apply_login_env_overrides(
        {"email": "user@example.local", "password": "devpassword123"},
    )

    assert updated == {
        "email": "bench@example.local",
        "password": "bench-password",
    }


def test_apply_login_env_overrides_returns_original_body_without_env():
    body = {"email": "user@example.local", "password": "devpassword123"}

    assert apply_login_env_overrides(body) is body
