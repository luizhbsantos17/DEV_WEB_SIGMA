from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint

from models.conversores import formatar_numero, para_data, para_decimal, texto
from models.db import db

UNIDADES = ["un", "m", "kg", "g", "rolo", "cx", "pç", "par"]


class ItemEstoque(db.Model):
    """Superclasse com os atributos e regras comuns a materiais e produtos."""

    __tablename__ = "itens_estoque"
    __table_args__ = (
        CheckConstraint(
            "quantidade >= 0", name="ck_item_quantidade_nao_negativa"
        ),  # RN01
        CheckConstraint("estoque_minimo >= 0", name="ck_item_minimo_nao_negativo"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    cor = db.Column(db.String(40))
    unidade_medida = db.Column(db.String(10), nullable=False)
    preco = db.Column(db.Numeric(10, 2))
    data_compra = db.Column(db.Date)
    estoque_minimo = db.Column(db.Numeric(12, 3), nullable=False)
    quantidade = db.Column(db.Numeric(12, 3), nullable=False, default=0)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    atualizado_em = db.Column(
        db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    __mapper_args__ = {"polymorphic_on": tipo, "polymorphic_identity": "item"}

    NOME_TIPO = "item"
    # Equivalente ao allowedFields do CI4: só estes campos podem vir do formulário.
    # quantidade, ativo, tipo e id NUNCA são preenchidos pelo usuário.
    CAMPOS_PERMITIDOS = [
        "nome",
        "cor",
        "unidade_medida",
        "preco",
        "data_compra",
        "estoque_minimo",
    ]

    def __init__(self, **kwargs):
        kwargs.setdefault("quantidade", Decimal("0"))
        kwargs.setdefault("ativo", True)
        super().__init__(**kwargs)

    # ---------- propriedades ----------
    @property
    def descricao(self):
        return " - ".join(parte for parte in (self.nome, self.cor) if parte)

    @property
    def em_alerta(self):
        """RN05 / D1: alerta quando o saldo atinge (fica menor ou igual a) o mínimo."""
        return self.ativo and self.quantidade <= self.estoque_minimo

    def possui_movimentacoes(self):
        from models.movimentacao import ItemMovimentado

        return (
            db.session.query(ItemMovimentado.id).filter_by(item_id=self.id).first()
            is not None
        )

    # ---------- validação ----------
    @classmethod
    def validar(cls, dados, novo=False):
        """Valida o formulário. Retorna (valores convertidos, erros em português)."""
        valores, erros = {}, {}

        nome = texto(dados, "nome")
        if not nome:
            erros["nome"] = f"Informe o nome do {cls.NOME_TIPO}."
        elif not 2 <= len(nome) <= 100:
            erros["nome"] = "O nome deve ter entre 2 e 100 caracteres."
        valores["nome"] = nome

        cor = texto(dados, "cor")
        if len(cor) > 40:
            erros["cor"] = "A cor deve ter no máximo 40 caracteres."
        valores["cor"] = cor or None

        unidade = texto(dados, "unidade_medida")
        if unidade not in UNIDADES:
            erros["unidade_medida"] = "Selecione uma unidade de medida."
        valores["unidade_medida"] = unidade

        valores["estoque_minimo"] = cls._ler_decimal(
            dados,
            "estoque_minimo",
            erros,
            obrigatorio=True,
            vazio="Informe o estoque mínimo.",
            negativo="O estoque mínimo não pode ser negativo.",
        )
        valores["preco"] = cls._ler_decimal(
            dados, "preco", erros, negativo="O preço não pode ser negativo."
        )

        try:
            data_compra = para_data(dados.get("data_compra"))
            if data_compra and data_compra > date.today():
                erros["data_compra"] = "A data da compra não pode ser futura."
        except ValueError:
            data_compra = None
            erros["data_compra"] = "Informe uma data válida."
        valores["data_compra"] = data_compra

        if novo:
            valores["quantidade_inicial"] = cls._ler_decimal(
                dados,
                "quantidade_inicial",
                erros,
                negativo="A quantidade inicial não pode ser negativa.",
            )

        return valores, erros

    @staticmethod
    def _ler_decimal(dados, campo, erros, obrigatorio=False, vazio="", negativo=""):
        try:
            valor = para_decimal(dados.get(campo))
        except ValueError:
            erros[campo] = "Informe um número válido (ex.: 12,5)."
            return None
        if valor is None and obrigatorio:
            erros[campo] = vazio
        elif valor is not None and valor < 0:
            erros[campo] = negativo
        return valor

    def preencher(self, valores):
        for campo in self.CAMPOS_PERMITIDOS:
            if campo in valores:
                setattr(self, campo, valores[campo])

    def para_formulario(self):
        return {
            "nome": self.nome,
            "cor": self.cor or "",
            "unidade_medida": self.unidade_medida,
            "preco": formatar_numero(self.preco) if self.preco is not None else "",
            "data_compra": self.data_compra.isoformat() if self.data_compra else "",
            "estoque_minimo": formatar_numero(self.estoque_minimo),
        }

    # ---------- operações ----------
    @classmethod
    def criar(cls, dados):
        """Cadastra o item. A quantidade inicial vira uma ENTRADA no histórico (RN04)."""
        from models.movimentacao import ItemMovimentado, Movimentacao

        valores, erros = cls.validar(dados, novo=True)
        if erros:
            return None, erros

        item = cls()
        item.preencher(valores)
        db.session.add(item)

        quantidade_inicial = valores.get("quantidade_inicial")
        if quantidade_inicial:
            movimentacao = Movimentacao(
                tipo="ENTRADA",
                data=valores["data_compra"] or date.today(),
                observacao="Saldo inicial do cadastro",
            )
            movimentacao.itens.append(
                ItemMovimentado(item=item, quantidade=quantidade_inicial)
            )
            item.quantidade = quantidade_inicial
            db.session.add(movimentacao)

        db.session.commit()
        return item, {}

    def atualizar(self, dados):
        valores, erros = self.validar(dados)
        if erros:
            return erros
        self.preencher(valores)
        db.session.commit()
        return {}

    def excluir_ou_inativar(self):
        """RN06 / D2: item com movimentações é inativado; sem movimentações, é excluído."""
        if self.possui_movimentacoes():
            self.ativo = False
            db.session.commit()
            return "inativado"
        db.session.delete(self)
        db.session.commit()
        return "excluido"

    def reativar(self):
        self.ativo = True
        db.session.commit()

    # ---------- consultas ----------
    @classmethod
    def listar(cls, busca="", inativos=False, pagina=1, por_pagina=20):
        consulta = cls.query.filter(cls.ativo.is_(not inativos))
        if busca:
            consulta = consulta.filter(cls.nome.ilike(f"%{busca}%"))
        return consulta.order_by(cls.nome).paginate(
            page=pagina, per_page=por_pagina, error_out=False
        )

    @classmethod
    def ativos(cls):
        return cls.query.filter_by(ativo=True).order_by(cls.tipo, cls.nome).all()

    @classmethod
    def todos(cls):
        return cls.query.order_by(cls.nome).all()

    @classmethod
    def resumo(cls):
        from models.material import Material
        from models.produto import Produto

        alertas = (
            cls.query.filter(cls.ativo.is_(True), cls.quantidade <= cls.estoque_minimo)
            .order_by(cls.nome)
            .all()
        )
        return {
            "total_materiais": Material.query.filter_by(ativo=True).count(),
            "total_produtos": Produto.query.filter_by(ativo=True).count(),
            "alertas": alertas,
        }
