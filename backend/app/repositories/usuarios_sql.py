"""
Persistencia de usuarios sobre SQLAlchemy.
=============================================

Implementa `domain.protocols.RepositorioUsuarios` contra cualquier base
soportada por SQLAlchemy. En la practica esto significa dos configuraciones:

  - **Desarrollo local y pruebas**: SQLite (archivo o `:memory:`). Cero
    infraestructura — el equipo clona el repo y corre `pytest` sin levantar
    nada. Es el mismo espiritu que `RepositorioMemoria` para el historial.

  - **Produccion (OCI)**: Postgres, vía `ATHENIA_DB_URL` (ver
    `docker-compose.yml`, servicio `athenia-db`). A diferencia del historial
    de contenidos, el equipo decidio en la Semana 5 que la base de usuarios
    SI necesita sobrevivir a un reinicio del contenedor: perder las cuentas
    registradas en plena demo no es aceptable.

El motor concreto lo decide unicamente la URL de conexion (`sqlite:///...` vs
`postgresql+psycopg2://...`); ni `dependencies.py` ni `routers/auth.py` saben
cual esta activo.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    create_engine,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool


class _Base(DeclarativeBase):
    pass


class UsuarioORM(_Base):
    """Tabla `usuarios`. Un registro por cuenta."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def _como_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "password_hash": self.password_hash,
            "nombre": self.nombre,
            "rol": self.rol,
            "creado_en": self.creado_en,
        }


class RepositorioUsuariosSQL:
    """
    `RepositorioUsuarios` sobre SQLAlchemy.

    Cada instancia abre su propio engine: en produccion se crea UNA vez en
    `dependencies.py` (ver `_repositorio_usuarios`); en pruebas cada caso
    puede pedir la suya con una URL `sqlite:///:memory:` distinta para
    aislarse por completo, sin tocar disco ni compartir estado entre tests.
    """

    def __init__(self, db_url: str) -> None:
        # SQLite necesita dos ajustes que Postgres no usa:
        #   - `check_same_thread=False`: uvicorn atiende peticiones sincronas
        #     desde un threadpool, no desde un unico hilo.
        #   - `StaticPool`: SIN esto, `sqlite:///:memory:` (el que usan las
        #     pruebas) le da una base EN BLANCO a cada conexion nueva del
        #     pool, y como cada hilo del threadpool abre la suya, un registro
        #     hecho en un request "desaparece" en el siguiente. `StaticPool`
        #     mantiene una unica conexion compartida para toda la vida del
        #     engine, evitando el problema. Es inofensivo tambien para el
        #     archivo de desarrollo (una sola conexion es de sobra para el
        #     trafico de una demo) y protegido por `self._lock` en cada metodo.
        es_sqlite = db_url.startswith("sqlite")
        args = {"check_same_thread": False} if es_sqlite else {}
        self._engine = create_engine(
            db_url,
            connect_args=args,
            poolclass=StaticPool if es_sqlite else None,
            future=True,
        )
        self._SesionLocal = sessionmaker(bind=self._engine, expire_on_commit=False)
        self._lock = threading.Lock()
        _Base.metadata.create_all(self._engine)

    # --- Escritura -----------------------------------------------------

    def crear(self, email: str, password_hash: str, nombre: str, rol: str) -> dict:
        email_normalizado = email.strip().lower()
        with self._lock, self._sesion() as sesion:
            registro = UsuarioORM(
                email=email_normalizado,
                password_hash=password_hash,
                nombre=nombre.strip(),
                rol=rol,
                creado_en=datetime.now(timezone.utc),
            )
            sesion.add(registro)
            try:
                sesion.commit()
            except IntegrityError as exc:
                sesion.rollback()
                raise ValueError(f"Ya existe una cuenta con el correo {email_normalizado}.") from exc
            sesion.refresh(registro)
            return registro._como_dict()

    # --- Lectura ---------------------------------------------------------

    def obtener_por_email(self, email: str) -> Optional[dict]:
        email_normalizado = email.strip().lower()
        with self._lock, self._sesion() as sesion:
            registro = sesion.execute(
                select(UsuarioORM).where(UsuarioORM.email == email_normalizado)
            ).scalar_one_or_none()
            return registro._como_dict() if registro else None

    def obtener_por_id(self, usuario_id: int) -> Optional[dict]:
        with self._lock, self._sesion() as sesion:
            registro = sesion.get(UsuarioORM, usuario_id)
            return registro._como_dict() if registro else None

    def listar(self) -> List[dict]:
        with self._lock, self._sesion() as sesion:
            registros = sesion.execute(
                select(UsuarioORM).order_by(UsuarioORM.id.desc())
            ).scalars()
            return [r._como_dict() for r in registros]

    def total(self) -> int:
        with self._lock, self._sesion() as sesion:
            return len(sesion.execute(select(UsuarioORM.id)).all())

    # --- Utilidad de pruebas ----------------------------------------------

    def limpiar(self) -> None:
        """Vacia la tabla. La usan las pruebas para aislarse entre casos."""
        with self._lock, self._sesion() as sesion:
            sesion.query(UsuarioORM).delete()
            sesion.commit()

    def _sesion(self) -> Session:
        return self._SesionLocal()
