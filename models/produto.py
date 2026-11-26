from models.conversores import texto
from models.db import db
from models.item_estoque import ItemEstoque

CATEGORIAS = ["Geral", "Infantil"]
GENEROS = ["Masculino", "Feminino", "Unissex"]
TAMANHOS_SUGERIDOS = [
    "PP",
    "P",
    "M",
    "G",
    "GG",
    "XG",
    "Único",
    "36",
    "38",
    "40",
    "42",
    "44",
    "46",
    "48",
]


class Produto(ItemEstoque):
    """Peça acabada, destinada à venda."""

    __tablename__ = "produtos"
    __table_args__ = (
        db.CheckConstraint("categoria IN ('Geral', 'Infantil')", name="ck_produto_categoria"),
    )
    id = db.Column(
        db.Integer,
        db.ForeignKey("itens_estoque.id", ondelete="CASCADE"),
        primary_key=True,
    )
    genero = db.Column(db.String(20), nullable=True)
    categoria = db.Column(db.String(20), nullable=False, server_default="Geral")
    tamanho = db.Column(db.String(10), nullable=False)

    __mapper_args__ = {"polymorphic_identity": "produto"}

    NOME_TIPO = "produto"
    CAMPOS_PERMITIDOS = ItemEstoque.CAMPOS_PERMITIDOS + ["genero", "categoria", "tamanho"]

    @property
    def descricao(self):
        return " - ".join(
            parte for parte in (f"{self.nome} {self.tamanho}", self.cor) if parte
        )

    @classmethod
    def validar(cls, dados, novo=False):
        valores, erros = super().validar(dados, novo)

        genero = texto(dados, "genero")
        if genero not in GENEROS:
            erros["genero"] = "Selecione o gênero do produto."
        valores["genero"] = genero

        categoria = texto(dados, "categoria") or "Geral"
        if categoria not in CATEGORIAS:
            erros["categoria"] = "Selecione uma categoria válida."
        valores["categoria"] = categoria

        tamanho = texto(dados, "tamanho")
        if not tamanho:
            erros["tamanho"] = "Informe o tamanho do produto."
        elif len(tamanho) > 10:
            erros["tamanho"] = "O tamanho deve ter no máximo 10 caracteres."
        valores["tamanho"] = tamanho

        return valores, erros

    def para_formulario(self):
        valores = super().para_formulario()
        valores["genero"] = self.genero or ""
        valores["categoria"] = self.categoria
        valores["tamanho"] = self.tamanho
        return valores
