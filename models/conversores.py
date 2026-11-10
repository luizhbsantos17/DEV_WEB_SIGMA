from datetime import datetime
from decimal import Decimal, InvalidOperation


def texto(dados, campo):
    """Lê um campo de texto do formulário sem espaços nas pontas."""
    return (dados.get(campo) or "").strip()


def para_decimal(valor):
    """Converte '12,5', '1.234,5' ou '12.5' em Decimal. Vazio vira None; inválido gera ValueError."""
    valor = (valor or "").strip().replace(" ", "")
    if not valor:
        return None
    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(valor)
    except InvalidOperation as erro:
        raise ValueError("número inválido") from erro
    if not numero.is_finite():
        raise ValueError("número inválido")
    return numero


def para_data(valor):
    """Converte 'aaaa-mm-dd' (campo date do HTML) em date. Vazio vira None; inválido gera ValueError."""
    valor = (valor or "").strip()
    if not valor:
        return None
    return datetime.strptime(valor, "%Y-%m-%d").date()


def data_ou_none(valor):
    """Usada em filtros: data inválida é simplesmente ignorada."""
    try:
        return para_data(valor)
    except ValueError:
        return None


def _padrao_brasileiro(texto_numero):
    return texto_numero.replace(",", "_").replace(".", ",").replace("_", ".")


def formatar_numero(valor, casas=3):
    """12.500 -> '12,5'; 1234 -> '1.234'."""
    if valor is None:
        return "-"
    texto_numero = f"{Decimal(valor):,.{casas}f}".rstrip("0").rstrip(".")
    return _padrao_brasileiro(texto_numero)


def formatar_moeda(valor):
    if valor is None:
        return "-"
    return "R$ " + _padrao_brasileiro(f"{Decimal(valor):,.2f}")


def formatar_data(valor):
    return valor.strftime("%d/%m/%Y") if valor else "-"
