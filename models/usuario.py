import re
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import CheckConstraint, literal, select

from models.db import db

SENHA_MINIMA = 8
SENHA_MAXIMA = 128

_hasher = PasswordHasher()
_hash_ausente = _hasher.hash(uuid4().hex)


def normalizar_login(login):
    return (login or "").strip().lower()


def erro_login(login):
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,39}", login):
        return "Use de 3 a 40 caracteres no login: letras, números, ponto, hífen ou sublinhado."


def erro_senha(senha):
    if len(senha) < SENHA_MINIMA:
        return f"Use pelo menos {SENHA_MINIMA} caracteres na senha."
    if len(senha) > SENHA_MAXIMA:
        return f"A senha pode ter até {SENHA_MAXIMA} caracteres."


class Usuario(db.Model):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint("perfil IN ('admin', 'funcionario')", name="ck_usuario_perfil"),
    )

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(40), nullable=False, unique=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    perfil = db.Column(db.String(15), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    troca_obrigatoria = db.Column(db.Boolean, nullable=False, default=False)
    versao_sessao = db.Column(db.String(32), nullable=False)

    __mapper_args__ = {
        "version_id_col": versao_sessao,
        "version_id_generator": lambda _: uuid4().hex,
    }

    @property
    def administrador(self):
        return self.perfil == "admin"

    @classmethod
    def administrador_existe(cls):
        consulta = select(cls.id).where(cls.perfil == "admin").limit(1)
        return db.session.scalar(consulta) is not None

    @classmethod
    def criar_primeiro_administrador(cls, login, senha):
        tabela = cls.__table__
        administrador = select(tabela.c.id).where(tabela.c.perfil == "admin").exists()
        # A verificação faz parte do INSERT para serializar a criação no SQLite.
        cadastro = select(
            literal(login), literal(_hasher.hash(senha)), literal("admin"),
            literal(True), literal(False), literal(uuid4().hex),
        ).where(~administrador)
        comando = tabela.insert().from_select(
            ["login", "senha_hash", "perfil", "ativo", "troca_obrigatoria", "versao_sessao"],
            cadastro,
        )
        criado = db.session.execute(comando).rowcount == 1
        db.session.commit()
        return criado

    def definir_senha(self, senha, temporaria=False):
        self.senha_hash = _hasher.hash(senha)
        self.troca_obrigatoria = temporaria

    @staticmethod
    def verificar_senha(usuario, senha):
        if not senha or len(senha) > SENHA_MAXIMA:
            return False
        senha_hash = usuario.senha_hash if usuario else _hash_ausente
        try:
            return _hasher.verify(senha_hash, senha)
        except VerifyMismatchError:
            return False
