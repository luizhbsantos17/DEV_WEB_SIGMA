from datetime import date

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from models import ItemEstoque, Movimentacao

bp = Blueprint("movimentacoes", __name__, url_prefix="/movimentacoes")


@bp.get("")
def listar():
    filtros = {
        campo: request.args.get(campo, "")
        for campo in ("item_id", "tipo", "data_inicio", "data_fim")
    }
    pagina = request.args.get("pagina", 1, type=int)
    paginacao = Movimentacao.historico(
        filtros, pagina, current_app.config["ITENS_POR_PAGINA"]
    )
    return render_template(
        "movimentacoes/lista.html",
        paginacao=paginacao,
        filtros=filtros,
        itens=ItemEstoque.todos(),
    )


def exibir_formulario(valores, linhas, erros):
    itens = ItemEstoque.ativos()
    return render_template(
        "movimentacoes/nova.html",
        itens=itens,
        itens_por_id={str(item.id): item for item in itens},
        valores=valores,
        linhas=linhas,
        erros=erros,
    )


@bp.get("/nova")
def nova():
    valores = {
        "tipo": request.args.get("tipo", "ENTRADA"),
        "data": date.today().isoformat(),
        "observacao": "",
    }
    linhas = [{"item_id": request.args.get("item_id", ""), "quantidade": ""}]
    return exibir_formulario(valores, linhas, [])


@bp.post("/registrar")
def registrar():
    movimentacao, erros = Movimentacao.registrar(request.form)
    if erros:
        linhas = [
            {"item_id": item_id, "quantidade": quantidade}
            for item_id, quantidade in zip(
                request.form.getlist("item_id"), request.form.getlist("quantidade")
            )
        ] or [{}]
        return exibir_formulario(request.form, linhas, erros)
    flash(f"{movimentacao.tipo_rotulo} registrada com sucesso.", "success")
    return redirect(url_for("movimentacoes.listar"))
