from datetime import date, datetime

from sqlalchemy import CheckConstraint, event

from models.conversores import (
    data_ou_none,
    formatar_numero,
    para_data,
    para_decimal,
    texto,
)
from models.db import db
from models.item_estoque import ItemEstoque


class Movimentacao(db.Model):
    """Entrada ou saída de estoque. Registro definitivo (RN03)."""

    __tablename__ = "movimentacoes"
    __table_args__ = (
        CheckConstraint("tipo IN ('ENTRADA', 'SAIDA')", name="ck_movimentacao_tipo"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(10), nullable=False)
    data = db.Column(db.Date, nullable=False)
    observacao = db.Column(db.String(255))
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)

    itens = db.relationship(
        "ItemMovimentado", back_populates="movimentacao", order_by="ItemMovimentado.id"
    )

    TIPOS = {"ENTRADA": "Entrada", "SAIDA": "Saída"}

    @property
    def tipo_rotulo(self):
        return self.TIPOS.get(self.tipo, self.tipo)

    @classmethod
    def registrar(cls, dados):
        """Registra uma entrada ou saída com um ou mais itens.

        Tudo ou nada: se alguma linha for inválida ou deixar saldo negativo (RN01),
        nada é gravado. O saldo é atualizado na mesma transação (RN04, RNF03).
        Retorna (movimentacao, erros).
        """
        erros = []

        tipo = texto(dados, "tipo").upper()
        if tipo not in cls.TIPOS:
            erros.append("Selecione o tipo da movimentação (entrada ou saída).")

        try:
            data_movimentacao = para_data(dados.get("data"))
            if data_movimentacao is None:
                erros.append("Informe a data da movimentação.")
            elif data_movimentacao > date.today():
                erros.append("A data da movimentação não pode ser futura.")
        except ValueError:
            data_movimentacao = None
            erros.append("Informe uma data válida.")

        observacao = texto(dados, "observacao")
        if len(observacao) > 255:
            erros.append("A observação deve ter no máximo 255 caracteres.")

        linhas = cls._ler_linhas(dados, erros)

        if tipo == "SAIDA":
            for item, quantidade in linhas:
                if quantidade > item.quantidade:
                    erros.append(
                        f"Saldo insuficiente para {item.descricao}: disponível "
                        f"{formatar_numero(item.quantidade)} {item.unidade_medida}."
                    )

        if erros:
            return None, erros

        movimentacao = cls(
            tipo=tipo, data=data_movimentacao, observacao=observacao or None
        )
        for item, quantidade in linhas:
            movimentacao.itens.append(ItemMovimentado(item=item, quantidade=quantidade))
            if tipo == "ENTRADA":
                item.quantidade += quantidade
            else:
                item.quantidade -= quantidade
        db.session.add(movimentacao)
        db.session.commit()
        return movimentacao, []

    @staticmethod
    def _ler_linhas(dados, erros):
        """Lê as linhas item_id/quantidade do formulário e valida cada uma."""
        linhas, vistos, preenchidas = [], set(), 0
        ids = dados.getlist("item_id")
        quantidades = dados.getlist("quantidade")

        for numero, (item_id, quantidade_texto) in enumerate(
            zip(ids, quantidades), start=1
        ):
            item_id = (item_id or "").strip()
            quantidade_texto = (quantidade_texto or "").strip()
            if not item_id and not quantidade_texto:
                continue
            preenchidas += 1

            item = (
                db.session.get(ItemEstoque, int(item_id)) if item_id.isdigit() else None
            )
            if item is None or not item.ativo:
                erros.append(f"Linha {numero}: selecione um item ativo.")
                continue
            if item.id in vistos:
                erros.append(
                    f"Linha {numero}: {item.descricao} já foi informado em outra linha."
                )
                continue
            vistos.add(item.id)

            try:
                quantidade = para_decimal(quantidade_texto)
            except ValueError:
                quantidade = None
            if quantidade is None or quantidade <= 0:
                erros.append(
                    f"Linha {numero}: informe uma quantidade maior que zero para {item.descricao}."
                )
                continue

            linhas.append((item, quantidade))

        if preenchidas == 0:
            erros.append("Adicione pelo menos um item à movimentação.")
        return linhas

    @classmethod
    def historico(cls, filtros, pagina=1, por_pagina=20):
        consulta = cls.query

        item_id = filtros.get("item_id", "")
        if item_id.isdigit():
            consulta = consulta.filter(
                cls.itens.any(ItemMovimentado.item_id == int(item_id))
            )
        if filtros.get("tipo") in cls.TIPOS:
            consulta = consulta.filter(cls.tipo == filtros["tipo"])

        data_inicio = data_ou_none(filtros.get("data_inicio"))
        if data_inicio:
            consulta = consulta.filter(cls.data >= data_inicio)
        data_fim = data_ou_none(filtros.get("data_fim"))
        if data_fim:
            consulta = consulta.filter(cls.data <= data_fim)

        return consulta.order_by(cls.data.desc(), cls.id.desc()).paginate(
            page=pagina, per_page=por_pagina, error_out=False
        )


class ItemMovimentado(db.Model):
    """Linha da movimentação: qual item e quanto (como a linha de uma nota fiscal)."""

    __tablename__ = "itens_movimentados"
    __table_args__ = (
        CheckConstraint(
            "quantidade > 0", name="ck_item_movimentado_quantidade_positiva"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    movimentacao_id = db.Column(
        db.Integer, db.ForeignKey("movimentacoes.id"), nullable=False
    )
    item_id = db.Column(db.Integer, db.ForeignKey("itens_estoque.id"), nullable=False)
    quantidade = db.Column(db.Numeric(12, 3), nullable=False)

    movimentacao = db.relationship("Movimentacao", back_populates="itens")
    item = db.relationship("ItemEstoque")


@event.listens_for(Movimentacao, "before_delete")
@event.listens_for(Movimentacao, "before_update")
@event.listens_for(ItemMovimentado, "before_delete")
@event.listens_for(ItemMovimentado, "before_update")
def bloquear_alteracao(_mapper, _conexao, _alvo):
    """RN03: a trilha de movimentações é definitiva."""
    raise RuntimeError(
        "Movimentações são definitivas e não podem ser alteradas nem apagadas (RN03)."
    )
