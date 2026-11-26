import os
from datetime import date

from flask import Flask, flash, g, redirect, render_template, url_for
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFError, CSRFProtect

from config import BASE_DIR, Config
from models import CATEGORIAS, GENEROS, TAMANHOS_SUGERIDOS, UNIDADES, db
from models.conversores import (
    formatar_data, formatar_data_hora, formatar_moeda, formatar_numero,
)
from models.usuario import SENHA_MAXIMA, SENHA_MINIMA

migrate = Migrate()
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if app.config.get("SECRET_KEY") in (None, "", "troque-por-uma-chave-longa-e-aleatoria"):
        raise RuntimeError(
            "SECRET_KEY não definida. Copie o arquivo .env.example para .env e defina uma chave."
        )

    os.makedirs(os.path.join(BASE_DIR, "database"), exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    from controllers.auth import criar_admin, verificar_acesso

    app.before_request(verificar_acesso)
    csrf.init_app(app)

    registrar_blueprints(app)
    registrar_templates(app)
    registrar_erros(app)

    from database.seed import seed_command

    app.cli.add_command(seed_command)
    app.cli.add_command(criar_admin)

    return app


def registrar_blueprints(app):
    from controllers.auth import admin_bp
    from controllers.auth import bp as auth_bp
    from controllers.dashboard import bp as dashboard_bp
    from controllers.materiais import bp as materiais_bp
    from controllers.movimentacoes import bp as movimentacoes_bp
    from controllers.produtos import bp as produtos_bp

    for blueprint in (auth_bp, admin_bp, dashboard_bp, materiais_bp, produtos_bp, movimentacoes_bp):
        app.register_blueprint(blueprint)


def registrar_templates(app):
    app.jinja_env.filters["numero"] = formatar_numero
    app.jinja_env.filters["moeda"] = formatar_moeda
    app.jinja_env.filters["data_br"] = formatar_data
    app.jinja_env.filters["data_hora_br"] = formatar_data_hora
    app.jinja_env.globals.update(
        UNIDADES=UNIDADES,
        CATEGORIAS=CATEGORIAS,
        GENEROS=GENEROS,
        TAMANHOS_SUGERIDOS=TAMANHOS_SUGERIDOS,
        SENHA_MINIMA=SENHA_MINIMA,
        SENHA_MAXIMA=SENHA_MAXIMA,
        hoje=lambda: date.today().isoformat(),
    )


def registrar_erros(app):
    @app.errorhandler(404)
    def pagina_nao_encontrada(erro):
        return render_template("erros/404.html"), 404

    @app.errorhandler(CSRFError)
    def csrf_invalido(erro):
        flash(
            "Sua sessão expirou ou o formulário é inválido. Tente novamente.", "warning"
        )
        return redirect(url_for("dashboard.index" if g.get("usuario") else "auth.login"))
