from models.conversores import texto
from models.db import db
from models.item_estoque import ItemEstoque


class Material(ItemEstoque):
    """Insumo (tecido, linha, aviamento) mantido em estoque."""

    __tablename__ = "materiais"
    id = db.Column(
        db.Integer,
        db.ForeignKey("itens_estoque.id", ondelete="CASCADE"),
        primary_key=True,
    )
    composicao = db.Column(db.String(100), nullable=False)

    __mapper_args__ = {"polymorphic_identity": "material"}

    NOME_TIPO = "material"
    CAMPOS_PERMITIDOS = ItemEstoque.CAMPOS_PERMITIDOS + ["composicao"]

    @classmethod
    def validar(cls, dados, novo=False):
        valores, erros = super().validar(dados, novo)
        composicao = texto(dados, "composicao")
        if not composicao:
            erros["composicao"] = (
                "Informe a composição do material (ex.: 100% algodão)."
            )
        elif len(composicao) > 100:
            erros["composicao"] = "A composição deve ter no máximo 100 caracteres."
        valores["composicao"] = composicao
        return valores, erros

    def para_formulario(self):
        valores = super().para_formulario()
        valores["composicao"] = self.composicao
        return valores
