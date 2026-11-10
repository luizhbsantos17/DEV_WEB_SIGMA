import os
from datetime import date

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFError, CSRFProtect

from config import BASE_DIR, Config
from models import GENEROS, TAMANHOS_SUGERIDOS, UNIDADES, db
from models.conversores import formatar_data, formatar_moeda, formatar_numero

migrate = Migrate()
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY não definida. Copie o arquivo .env.example para .env e defina uma chave."
        )

    os.makedirs(os.path.join(BASE_DIR, "database"), exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    csrf.init_app(app)

    registrar_blueprints(app)
    registrar_templates(app)
    registrar_erros(app)

    from database.seed import seed_command

    app.cli.add_command(seed_command)

    return app


def registrar_blueprints(app):
    from controllers.dashboard import bp as dashboard_bp
    from controllers.materiais import bp as materiais_bp
    from controllers.movimentacoes import bp as movimentacoes_bp
    from controllers.produtos import bp as produtos_bp

    for blueprint in (dashboard_bp, materiais_bp, produtos_bp, movimentacoes_bp):
        app.register_blueprint(blueprint)


def registrar_templates(app):
    app.jinja_env.filters["numero"] = formatar_numero
    app.jinja_env.filters["moeda"] = formatar_moeda
    app.jinja_env.filters["data_br"] = formatar_data
    app.jinja_env.globals.update(
        UNIDADES=UNIDADES,
        GENEROS=GENEROS,
        TAMANHOS_SUGERIDOS=TAMANHOS_SUGERIDOS,
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
        return redirect(url_for("dashboard.index"))
