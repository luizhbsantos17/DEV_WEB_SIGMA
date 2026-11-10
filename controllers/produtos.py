from controllers.itens import criar_blueprint_itens
from models import Produto

bp = criar_blueprint_itens("produtos", Produto, titulo="Produtos", singular="Produto")
