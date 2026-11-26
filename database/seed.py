from datetime import date, timedelta
from decimal import Decimal

import click
from flask.cli import with_appcontext

from models import ItemEstoque, ItemMovimentado, Material, Movimentacao, Produto, db


@click.command("seed")
@with_appcontext
def seed_command():
    """Popula o banco com dados de exemplo para a demonstração."""
    if ItemEstoque.query.first():
        click.echo("O banco já possui itens; nada foi alterado.")
        return

    hoje = date.today()

    def material(nome, cor, unidade, preco, minimo, composicao):
        return Material(
            nome=nome,
            cor=cor,
            unidade_medida=unidade,
            preco=Decimal(preco),
            estoque_minimo=Decimal(minimo),
            composicao=composicao,
            data_compra=hoje - timedelta(days=20),
        )

    def produto(nome, cor, preco, minimo, genero, tamanho, categoria="Geral"):
        return Produto(
            nome=nome,
            cor=cor,
            unidade_medida="un",
            preco=Decimal(preco),
            estoque_minimo=Decimal(minimo),
            genero=genero,
            tamanho=tamanho,
            categoria=categoria,
        )

    malha = material(
        "Malha algodão penteado", "Branco", "m", "18.90", "30", "100% algodão"
    )
    tricoline = material(
        "Tecido tricoline", "Azul marinho", "m", "22.50", "20", "100% algodão"
    )
    linha = material(
        "Linha de costura", "Preto", "rolo", "6.50", "10", "100% poliéster"
    )
    elastico = material(
        "Elástico chato 3 cm", "Branco", "m", "1.20", "50", "Poliéster/elastano"
    )
    botao = material("Botão 4 furos", "Bege", "un", "0.15", "200", "Poliéster")
    ziper = material("Zíper 15 cm", "Preto", "un", "1.80", "40", "Nylon")

    camiseta_m = produto("Camiseta básica", "Branco", "39.90", "10", "Unissex", "M")
    camiseta_g = produto("Camiseta básica", "Branco", "39.90", "10", "Unissex", "G")
    calca = produto("Calça jeans", "Azul", "129.90", "5", "Feminino", "40")
    vestido = produto("Vestido infantil", "Rosa", "79.90", "4", "Feminino", "Único", "Infantil")
    bermuda = produto("Bermuda sarja", "Cáqui", "69.90", "5", "Masculino", "42")

    db.session.add_all(
        [
            malha,
            tricoline,
            linha,
            elastico,
            botao,
            ziper,
            camiseta_m,
            camiseta_g,
            calca,
            vestido,
            bermuda,
        ]
    )

    def movimentar(tipo, dias_atras, observacao, linhas):
        movimentacao = Movimentacao(
            tipo=tipo, data=hoje - timedelta(days=dias_atras), observacao=observacao
        )
        for item, quantidade in linhas:
            quantidade = Decimal(quantidade)
            movimentacao.itens.append(ItemMovimentado(item=item, quantidade=quantidade))
            if tipo == "ENTRADA":
                item.quantidade += quantidade
            else:
                item.quantidade -= quantidade
        db.session.add(movimentacao)

    movimentar(
        "ENTRADA",
        20,
        "Compra do fornecedor Têxtil Sul",
        [
            (malha, "120"),
            (tricoline, "60"),
            (linha, "25"),
            (elastico, "200"),
            (botao, "1000"),
        ],
    )
    movimentar(
        "ENTRADA",
        15,
        "Produção da semana",
        [
            (camiseta_m, "40"),
            (camiseta_g, "30"),
            (calca, "12"),
            (vestido, "8"),
            (bermuda, "6"),
        ],
    )
    movimentar(
        "SAIDA", 10, "Uso na produção", [(malha, "95"), (linha, "12"), (elastico, "80")]
    )
    movimentar(
        "SAIDA",
        5,
        "Vendas da semana",
        [(camiseta_m, "32"), (calca, "4"), (vestido, "2"), (bermuda, "6")],
    )
    movimentar("SAIDA", 2, "Uso na produção", [(tricoline, "15"), (botao, "300")])

    bermuda.ativo = False  # item com movimentações inativado (RN06)

    db.session.commit()
    click.echo("Dados de exemplo criados.")
