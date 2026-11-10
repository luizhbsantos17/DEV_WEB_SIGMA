from flask import Blueprint, render_template

from models import ItemEstoque

bp = Blueprint("dashboard", __name__)


@bp.get("/")
@bp.get("/dashboard")
def index():
    return render_template("dashboard/index.html", resumo=ItemEstoque.resumo())
