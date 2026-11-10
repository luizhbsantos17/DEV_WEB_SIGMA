from models.conversores import texto
from models.db import db
from models.item_estoque import ItemEstoque

GENEROS = ["Masculino", "Feminino", "Unissex", "Infantil"]
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
    id = db.Column(
        db.Integer,
        db.ForeignKey("itens_estoque.id", ondelete="CASCADE"),
        primary_key=True,
    )
    genero = db.Column(db.String(20), nullable=False)
    tamanho = db.Column(db.String(10), nullable=False)

    __mapper_args__ = {"polymorphic_identity": "produto"}

    NOME_TIPO = "produto"
    CAMPOS_PERMITIDOS = ItemEstoque.CAMPOS_PERMITIDOS + ["genero", "tamanho"]

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

        tamanho = texto(dados, "tamanho")
        if not tamanho:
            erros["tamanho"] = "Informe o tamanho do produto."
        elif len(tamanho) > 10:
            erros["tamanho"] = "O tamanho deve ter no máximo 10 caracteres."
        valores["tamanho"] = tamanho

        return valores, erros

    def para_formulario(self):
        valores = super().para_formulario()
        valores["genero"] = self.genero
        valores["tamanho"] = self.tamanho
        return valores
