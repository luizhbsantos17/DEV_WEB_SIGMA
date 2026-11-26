from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from models import db


def criar_blueprint_itens(nome, modelo, titulo, singular):
    """Cria o Blueprint com o CRUD de um tipo de item (materiais ou produtos)."""
    bp = Blueprint(nome, __name__, url_prefix=f"/{nome}")
    secao = {
        "nome": nome,
        "titulo": titulo,
        "singular": singular,
        "tipo": modelo.NOME_TIPO,
    }

    def buscar_ou_404(item_id):
        item = db.session.get(modelo, item_id)
        if item is None:
            abort(404)
        return item

    def exibir_formulario(valores, erros, item=None):
        acao = (
            url_for(f"{nome}.atualizar", item_id=item.id)
            if item
            else url_for(f"{nome}.salvar")
        )
        return render_template(
            "itens/form.html",
            secao=secao,
            valores=valores,
            erros=erros,
            item=item,
            acao=acao,
        )

    @bp.get("")
    def listar():
        busca = request.args.get("q", "").strip()
        inativos = request.args.get("status") == "inativos"
        pagina = request.args.get("pagina", 1, type=int)
        paginacao = modelo.listar(
            busca, inativos, pagina, current_app.config["ITENS_POR_PAGINA"]
        )
        return render_template(
            "itens/lista.html",
            secao=secao,
            paginacao=paginacao,
            busca=busca,
            inativos=inativos,
        )

    @bp.get("/novo")
    def novo():
        return exibir_formulario({"categoria": "Geral"} if modelo.NOME_TIPO == "produto" else {}, {})

    @bp.post("/salvar")
    def salvar():
        item, erros = modelo.criar(request.form)
        if erros:
            flash("Corrija os campos destacados.", "danger")
            return exibir_formulario(request.form, erros)
        flash(f'{singular} "{item.descricao}" cadastrado com sucesso.', "success")
        return redirect(url_for(f"{nome}.listar"))

    @bp.get("/editar/<int:item_id>")
    def editar(item_id):
        item = buscar_ou_404(item_id)
        if not item.ativo:
            flash("Reative o item antes de editá-lo.", "warning")
            return redirect(url_for(f"{nome}.listar", status="inativos"))
        return exibir_formulario(item.para_formulario(), {}, item)

    @bp.post("/atualizar/<int:item_id>")
    def atualizar(item_id):
        item = buscar_ou_404(item_id)
        erros = item.atualizar(request.form)
        if erros:
            flash("Corrija os campos destacados.", "danger")
            return exibir_formulario(request.form, erros, item)
        flash(f'{singular} "{item.descricao}" atualizado com sucesso.', "success")
        return redirect(url_for(f"{nome}.listar"))

    @bp.post("/excluir/<int:item_id>")
    def excluir(item_id):
        item = buscar_ou_404(item_id)
        descricao = item.descricao
        if item.excluir_ou_inativar() == "inativado":
            flash(
                f'"{descricao}" possui movimentações e foi inativado em vez de excluído.',
                "warning",
            )
        else:
            flash(f'"{descricao}" excluído com sucesso.', "success")
        return redirect(url_for(f"{nome}.listar"))

    @bp.post("/reativar/<int:item_id>")
    def reativar(item_id):
        item = buscar_ou_404(item_id)
        item.reativar()
        flash(f'"{item.descricao}" reativado.', "success")
        return redirect(url_for(f"{nome}.listar"))

    return bp
