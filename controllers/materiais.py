from controllers.itens import criar_blueprint_itens
from models import Material

bp = criar_blueprint_itens(
    "materiais", Material, titulo="Materiais", singular="Material"
)
