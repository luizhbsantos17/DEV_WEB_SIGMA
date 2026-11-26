from urllib.parse import urlsplit

import click
from flask import (
    Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for,
)
from flask.cli import with_appcontext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from models.db import db
from models.usuario import Usuario, erro_login, erro_senha, normalizar_login

bp = Blueprint("auth", __name__)
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
LOGIN_INICIAL = "admin"


def verificar_acesso():
    endpoint = request.endpoint
    if endpoint in (None, "static"):
        return

    usuario_id = session.get("usuario_id")
    usuario = db.session.get(Usuario, usuario_id) if usuario_id else None
    if usuario and usuario.ativo and usuario.versao_sessao == session.get("versao_sessao"):
        g.usuario = usuario
    else:
        if usuario_id:
            session.clear()
        if endpoint not in ("auth.login", "auth.configuracao_inicial"):
            return redirect(url_for("auth.login"))
        return

    if endpoint == "auth.sair":
        return
    if usuario.troca_obrigatoria and endpoint != "auth.trocar_senha":
        return redirect(url_for("auth.trocar_senha"))


@admin_bp.before_request
def verificar_administrador():
    if not g.usuario.administrador:
        abort(403)


def iniciar_sessao(usuario):
    session.clear()
    session.permanent = True
    session["usuario_id"] = usuario.id
    session["versao_sessao"] = usuario.versao_sessao


def configuracao_local():
    if current_app.config["SESSION_COOKIE_SECURE"]:
        return False
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return False
    if any(
        nome == "Forwarded" or nome == "X-Real-Ip" or nome.startswith("X-Forwarded-")
        for nome in request.headers.keys()
    ):
        return False
    return urlsplit(request.host_url).hostname in ("localhost", "127.0.0.1", "::1")


@bp.route("/configuracao-inicial", methods=["GET", "POST"])
def configuracao_inicial():
    if not configuracao_local():
        abort(403)
    if Usuario.administrador_existe():
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        senha = request.form.get("senha", "")
        erro = erro_senha(senha)
        if not erro and senha != request.form.get("confirmacao"):
            erro = "As senhas devem ser iguais."
        if erro:
            flash(erro, "danger")
            return render_template("auth/configuracao.html", login=LOGIN_INICIAL), 400

        try:
            criado = Usuario.criar_primeiro_administrador(LOGIN_INICIAL, senha)
        except IntegrityError:
            db.session.rollback()
            flash("O login admin já está em uso.", "danger")
            return render_template("auth/configuracao.html", login=LOGIN_INICIAL), 409
        if not criado:
            return redirect(url_for("auth.login"))

        usuario = Usuario.query.filter_by(login=LOGIN_INICIAL, perfil="admin").one()
        iniciar_sessao(usuario)
        flash("Conta de administrador criada.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/configuracao.html", login=LOGIN_INICIAL)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.get("usuario"):
        return redirect(url_for("dashboard.index"))
    if configuracao_local() and not Usuario.administrador_existe():
        return redirect(url_for("auth.configuracao_inicial"))
    nome = ""
    if request.method == "POST":
        nome = normalizar_login(request.form.get("login"))
        usuario = None
        if not erro_login(nome):
            usuario = Usuario.query.filter_by(login=nome).one_or_none()
        senha_valida = Usuario.verificar_senha(usuario, request.form.get("senha", ""))
        if usuario and usuario.ativo and senha_valida:
            iniciar_sessao(usuario)
            destino = "auth.trocar_senha" if usuario.troca_obrigatoria else "dashboard.index"
            return redirect(url_for(destino))
        flash("Login ou senha inválidos.", "danger")
        return render_template("auth/login.html", login=nome), 401
    return render_template("auth/login.html", login=nome)


@bp.post("/sair")
def sair():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/conta/senha", methods=["GET", "POST"])
def trocar_senha():
    usuario = g.usuario
    if request.method == "POST":
        atual = request.form.get("senha_atual", "")
        nova = request.form.get("senha", "")
        erro = erro_senha(nova)
        if not Usuario.verificar_senha(usuario, atual):
            erro = "Senha atual inválida."
        elif nova != request.form.get("confirmacao"):
            erro = "As novas senhas devem ser iguais."
        elif nova == atual:
            erro = "Escolha uma senha diferente da atual."

        if erro:
            flash(erro, "danger")
        else:
            usuario.definir_senha(nova)
            try:
                db.session.commit()
            except StaleDataError:
                db.session.rollback()
                session.clear()
                flash("A conta foi alterada. Entre novamente.", "warning")
                return redirect(url_for("auth.login"))
            iniciar_sessao(usuario)
            flash("Senha alterada.", "success")
            return redirect(url_for("dashboard.index"))
    return render_template("auth/senha.html")


@admin_bp.get("/funcionarios")
def funcionarios():
    funcionarios = Usuario.query.filter_by(perfil="funcionario").order_by(Usuario.login).all()
    return render_template("auth/funcionarios.html", funcionarios=funcionarios)


@admin_bp.post("/funcionarios")
def criar_funcionario():
    login = normalizar_login(request.form.get("login"))
    senha = request.form.get("senha", "")
    erro = erro_login(login) or erro_senha(senha)
    if erro:
        flash(erro, "danger")
    else:
        funcionario = Usuario(login=login, perfil="funcionario")
        funcionario.definir_senha(senha, temporaria=True)
        db.session.add(funcionario)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Já existe uma conta com esse login.", "danger")
        else:
            flash(f"Conta de {login} criada.", "success")
    return redirect(url_for("admin.funcionarios"))


def buscar_funcionario(usuario_id):
    funcionario = db.session.get(Usuario, usuario_id)
    if not funcionario or funcionario.administrador:
        abort(404)
    return funcionario


def salvar_funcionario(mensagem):
    try:
        db.session.commit()
    except StaleDataError:
        db.session.rollback()
        flash("A conta foi alterada em outra sessão. Tente novamente.", "warning")
    else:
        flash(mensagem, "success")
    return redirect(url_for("admin.funcionarios"))


@admin_bp.post("/funcionarios/<int:usuario_id>/status")
def status_funcionario(usuario_id):
    funcionario = buscar_funcionario(usuario_id)
    status = request.form.get("ativo")
    if status not in ("0", "1"):
        abort(400)
    funcionario.ativo = status == "1"
    return salvar_funcionario("Situação da conta atualizada.")


@admin_bp.post("/funcionarios/<int:usuario_id>/senha")
def senha_funcionario(usuario_id):
    funcionario = buscar_funcionario(usuario_id)
    senha = request.form.get("senha", "")
    erro = erro_senha(senha)
    if erro:
        flash(erro, "danger")
        return redirect(url_for("admin.funcionarios"))
    funcionario.definir_senha(senha, temporaria=True)
    return salvar_funcionario("Senha temporária definida. As sessões anteriores foram encerradas.")


@click.command("criar-admin")
@click.argument("login")
@with_appcontext
def criar_admin(login):
    """Cria a primeira conta de administrador."""
    login = normalizar_login(login)
    erro = erro_login(login)
    if erro:
        raise click.ClickException(erro)
    if Usuario.administrador_existe():
        raise click.ClickException("Já existe uma conta de administrador.")
    senha = click.prompt("Senha", hide_input=True, confirmation_prompt=True)
    erro = erro_senha(senha)
    if erro:
        raise click.ClickException(erro)
    try:
        criado = Usuario.criar_primeiro_administrador(login, senha)
    except IntegrityError as erro_db:
        db.session.rollback()
        raise click.ClickException("Já existe uma conta com esse login.") from erro_db
    if not criado:
        raise click.ClickException("Já existe uma conta de administrador.")
    click.echo(f"Administrador {login} criado.")
