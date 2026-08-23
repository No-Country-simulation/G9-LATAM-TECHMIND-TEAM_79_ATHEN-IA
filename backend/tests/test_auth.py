"""
Suite de pruebas de autenticacion y usuarios (Semana 5) - QA AthenIA.
=========================================================================

Cubre el modulo agregado para resolver el pendiente de login + base de
usuarios detectado por el equipo antes del Demo Day:

    POST /auth/registro    201 con token / 409 si el correo ya existe
    POST /auth/login       200 con token / 401 con credenciales invalidas
    GET  /auth/me          200 con el usuario del token / 401 sin token
    GET  /auth/usuarios    200 solo para 'admin' / 403 para 'estudiante'

Cada caso usa su propio repositorio SQLite en memoria (nunca el archivo de
desarrollo ni Postgres), inyectado via `app.dependency_overrides` — el mismo
mecanismo que ya usa la suite para `get_buscador_cursos`.

Ejecutar desde la raiz del repositorio:

    pytest backend/tests/test_auth.py -v
"""

from __future__ import annotations

import pytest

from app.dependencies import get_repositorio_usuarios
from app.main import app
from app.repositories.usuarios_sql import RepositorioUsuariosSQL

# ===========================================================================
# Fixtures locales
# ===========================================================================


@pytest.fixture
def repo_usuarios():
    """
    Un repositorio de usuarios SQLite en memoria, aislado por test.

    `sqlite:///:memory:` con `check_same_thread=False` crea una base nueva y
    vacia para cada test — nunca toca `backend/data/athenia_usuarios.db` (el
    archivo real de desarrollo) ni Postgres.
    """
    return RepositorioUsuariosSQL("sqlite:///:memory:")


@pytest.fixture
def client(client, repo_usuarios):
    """
    Sustituye `get_repositorio_usuarios` por el repositorio en memoria de este
    test, y restaura el override anterior al terminar.

    Reutiliza el fixture `client` de `conftest.py` (sesion completa, mismo
    `TestClient`) en vez de crear uno nuevo: es el mismo patron que usan
    `test_recomendaciones.py` y `test_analiticas.py`.
    """
    app.dependency_overrides[get_repositorio_usuarios] = lambda: repo_usuarios
    yield client
    del app.dependency_overrides[get_repositorio_usuarios]


@pytest.fixture
def credenciales_validas() -> dict:
    return {"email": "ferney@athenia.dev", "password": "unaClaveSegura123", "nombre": "Ferney"}


def _registrar(client, credenciales=None) -> dict:
    """Atajo: registra un usuario y devuelve el cuerpo de la respuesta."""
    return client.post("/auth/registro", json=credenciales or {
        "email": "ferney@athenia.dev",
        "password": "unaClaveSegura123",
        "nombre": "Ferney",
    }).json()


# ===========================================================================
# CP-300..CP-304 | Registro
# ===========================================================================


def test_registro_devuelve_201_y_token(client, credenciales_validas):
    """CP-300: un registro valido responde 201 con token y usuario."""
    respuesta = client.post("/auth/registro", json=credenciales_validas)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"
    assert isinstance(cuerpo["access_token"], str) and cuerpo["access_token"]
    assert cuerpo["usuario"]["email"] == "ferney@athenia.dev"
    assert cuerpo["usuario"]["nombre"] == "Ferney"
    assert "password" not in cuerpo["usuario"]
    assert "password_hash" not in cuerpo["usuario"]


def test_primer_usuario_registrado_es_admin(client, credenciales_validas):
    """CP-301: la primera cuenta de una instalacion nueva recibe el rol admin."""
    cuerpo = _registrar(client, credenciales_validas)
    assert cuerpo["usuario"]["rol"] == "admin"


def test_segundo_usuario_registrado_es_estudiante(client, credenciales_validas):
    """CP-302: a partir del segundo registro, el rol por defecto es estudiante."""
    _registrar(client, credenciales_validas)

    segundo = client.post(
        "/auth/registro",
        json={"email": "luis@athenia.dev", "password": "otraClaveSegura456", "nombre": "Luis"},
    ).json()

    assert segundo["usuario"]["rol"] == "estudiante"


def test_registro_con_correo_duplicado_devuelve_409(client, credenciales_validas):
    """CP-303: registrar el mismo correo dos veces responde 409, no 500."""
    _registrar(client, credenciales_validas)

    repetido = client.post("/auth/registro", json=credenciales_validas)

    assert repetido.status_code == 409


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("email", "no-es-un-correo"),
        ("password", "corta"),  # menos de 8 caracteres
        ("nombre", "   "),
    ],
)
def test_registro_con_datos_invalidos_devuelve_422(client, credenciales_validas, campo, valor):
    """CP-304: email sin formato, password corto o nombre vacio responden 422."""
    payload = {**credenciales_validas, campo: valor}
    respuesta = client.post("/auth/registro", json=payload)
    assert respuesta.status_code == 422


def test_email_se_normaliza_a_minusculas(client):
    """CP-305: 'Ferney@Athenia.DEV' y 'ferney@athenia.dev' son la misma cuenta."""
    _registrar(client, {
        "email": "Ferney@Athenia.DEV",
        "password": "unaClaveSegura123",
        "nombre": "Ferney",
    })

    duplicado = client.post(
        "/auth/registro",
        json={"email": "ferney@athenia.dev", "password": "otraClaveSegura456", "nombre": "Ferney 2"},
    )
    assert duplicado.status_code == 409


# ===========================================================================
# CP-310..CP-313 | Login
# ===========================================================================


def test_login_con_credenciales_correctas_devuelve_token(client, credenciales_validas):
    """CP-310: login con el email y password correctos responde 200 con token."""
    _registrar(client, credenciales_validas)

    respuesta = client.post(
        "/auth/login",
        json={"email": credenciales_validas["email"], "password": credenciales_validas["password"]},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["usuario"]["email"] == credenciales_validas["email"]
    assert cuerpo["access_token"]


def test_login_con_password_incorrecta_devuelve_401(client, credenciales_validas):
    """CP-311: password incorrecta responde 401, nunca 500 ni filtra si el correo existe."""
    _registrar(client, credenciales_validas)

    respuesta = client.post(
        "/auth/login",
        json={"email": credenciales_validas["email"], "password": "claveIncorrecta"},
    )

    assert respuesta.status_code == 401


def test_login_con_correo_inexistente_devuelve_401(client):
    """CP-312: un correo que nunca se registro responde 401, no 404."""
    respuesta = client.post(
        "/auth/login", json={"email": "nadie@athenia.dev", "password": "cualquierClave123"}
    )
    assert respuesta.status_code == 401


def test_login_es_insensible_a_mayusculas_en_el_correo(client, credenciales_validas):
    """CP-313: el login normaliza el correo igual que el registro."""
    _registrar(client, credenciales_validas)

    respuesta = client.post(
        "/auth/login",
        json={"email": "FERNEY@ATHENIA.DEV", "password": credenciales_validas["password"]},
    )
    assert respuesta.status_code == 200


# ===========================================================================
# CP-320..CP-323 | Sesion (/auth/me) y control de acceso por rol
# ===========================================================================


def test_me_sin_token_devuelve_401(client):
    """CP-320: consultar /auth/me sin header Authorization responde 401."""
    respuesta = client.get("/auth/me")
    assert respuesta.status_code == 401


def test_me_con_token_valido_devuelve_el_usuario(client, credenciales_validas):
    """CP-321: el token emitido en el registro autentica correctamente en /auth/me."""
    token = _registrar(client, credenciales_validas)["access_token"]

    respuesta = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    assert respuesta.json()["email"] == credenciales_validas["email"]


def test_me_con_token_invalido_devuelve_401(client):
    """CP-322: un token con formato de JWT pero firma invalida responde 401, no 500."""
    respuesta = client.get(
        "/auth/me", headers={"Authorization": "Bearer esto.no.es-un-token-valido"}
    )
    assert respuesta.status_code == 401


def test_usuarios_admin_permite_a_un_admin(client, credenciales_validas):
    """CP-323: el primer usuario (admin) puede listar el catalogo de cuentas."""
    token_admin = _registrar(client, credenciales_validas)["access_token"]

    respuesta = client.get("/auth/usuarios", headers={"Authorization": f"Bearer {token_admin}"})

    assert respuesta.status_code == 200
    correos = [u["email"] for u in respuesta.json()]
    assert credenciales_validas["email"] in correos


def test_usuarios_admin_rechaza_a_un_estudiante(client, credenciales_validas):
    """CP-324: un usuario con rol 'estudiante' recibe 403 aunque su token sea valido."""
    _registrar(client, credenciales_validas)  # admin (primero)

    token_estudiante = client.post(
        "/auth/registro",
        json={"email": "luis@athenia.dev", "password": "otraClaveSegura456", "nombre": "Luis"},
    ).json()["access_token"]

    respuesta = client.get(
        "/auth/usuarios", headers={"Authorization": f"Bearer {token_estudiante}"}
    )

    assert respuesta.status_code == 403
