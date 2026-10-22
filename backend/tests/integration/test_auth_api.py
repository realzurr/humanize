"""Testes de integração da autenticação (registro, login, me)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _registrar_e_logar(client: TestClient, username: str) -> str:
    resposta = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "senha-forte-123"},
    )
    assert resposta.status_code == 201
    token = client.post(
        "/api/v1/auth/token",
        json={"username": username, "password": "senha-forte-123"},
    ).json()["access_token"]
    return token


def test_registro_login_e_me(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        token = _registrar_e_logar(client, "alice")
        resposta = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resposta.status_code == 200
        assert resposta.json()["username"] == "alice"


def test_login_com_senha_errada(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        client.post(
            "/api/v1/auth/register",
            json={"username": "bob", "password": "senha-forte-123"},
        )
        resposta = client.post(
            "/api/v1/auth/token",
            json={"username": "bob", "password": "senha-errada"},
        )
        assert resposta.status_code == 401


def test_registro_duplicado_retorna_conflito(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        corpo = {"username": "carol", "password": "senha-forte-123"}
        assert client.post("/api/v1/auth/register", json=corpo).status_code == 201
        assert client.post("/api/v1/auth/register", json=corpo).status_code == 409


def test_me_sem_token_retorna_401(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        assert client.get("/api/v1/auth/me").status_code == 401


def test_token_adulterado_retorna_401(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        token = _registrar_e_logar(client, "dave")
        resposta = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}x"})
        assert resposta.status_code == 401


def test_username_invalido_rejeitado(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        resposta = client.post(
            "/api/v1/auth/register",
            json={"username": "a b!", "password": "senha-forte-123"},
        )
        assert resposta.status_code == 422


def test_logout_revoga_token_e_rehash_pbkdf2_no_login(app_with_auth, db_session_factory) -> None:
    from app.core.security import hash_password
    from app.repositories.users import UserRepository

    with db_session_factory() as session:
        repo = UserRepository(session)
        repo.create("legado_user", hash_password("senha-forte-123", algorithm="pbkdf2_sha256"))

    with TestClient(app_with_auth) as client:
        resp_login = client.post(
            "/api/v1/auth/token",
            json={"username": "legado_user", "password": "senha-forte-123"},
        )
        assert resp_login.status_code == 200
        token = resp_login.json()["access_token"]

        # Hash foi atualizado transparentemente para argon2id
        with db_session_factory() as session:
            atualizado = UserRepository(session).get_by_username("legado_user")
            assert atualizado is not None
            assert atualizado.password_hash.startswith("argon2id$")

        # Logout revoga o token
        resp_logout = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_logout.status_code == 204

        resp_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp_me.status_code == 401


def test_logout_all_revoga_todas_as_sessoes_do_usuario(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        credenciais = {"username": "multi", "password": "senha-forte-123"}
        client.post("/api/v1/auth/register", json=credenciais)
        outro = {"username": "intacto", "password": "senha-forte-123"}
        client.post("/api/v1/auth/register", json=outro)

        notebook = client.post("/api/v1/auth/token", json=credenciais).json()["access_token"]
        celular = client.post("/api/v1/auth/token", json=credenciais).json()["access_token"]
        token_outro = client.post("/api/v1/auth/token", json=outro).json()["access_token"]

        resposta = client.post(
            "/api/v1/auth/logout-all", headers={"Authorization": f"Bearer {notebook}"}
        )
        assert resposta.status_code == 204

        for token in (notebook, celular):
            me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert me.status_code == 401
        me_outro = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_outro}"})
        assert me_outro.status_code == 200

        # Novo login após o corte continua funcionando.
        novo = client.post("/api/v1/auth/token", json=credenciais).json()["access_token"]
        me_novo = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {novo}"})
        assert me_novo.status_code == 200


def test_logout_all_exige_autenticacao(app_with_auth) -> None:
    with TestClient(app_with_auth) as client:
        assert client.post("/api/v1/auth/logout-all").status_code == 401
