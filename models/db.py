import sqlite3
import warnings

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

# O SQLite guarda decimais como número; o aviso do SQLAlchemy sobre isso não afeta o sistema.
warnings.filterwarnings("ignore", message=".*Decimal objects natively")

db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def ativar_chaves_estrangeiras(conexao, _registro):
    """O SQLite só respeita chaves estrangeiras com este PRAGMA ligado."""
    if isinstance(conexao, sqlite3.Connection):
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
