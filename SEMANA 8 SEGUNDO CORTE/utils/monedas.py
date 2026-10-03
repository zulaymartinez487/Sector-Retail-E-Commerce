"""
Monedas soportadas por el marketplace.

Los precios se guardan SIEMPRE en pesos colombianos (COP) y solo se
convierten al mostrarlos o al cobrar. Las tasas son fijas (de referencia)
para el proyecto; en producción se consultarían a un servicio de tasas.
"""

MONEDA_BASE = "COP"

MONEDAS = {
    "COP": {"nombre": "Peso colombiano", "simbolo": "$", "por_cop": 1, "decimales": 0},
    "USD": {"nombre": "Dólar estadounidense", "simbolo": "US$", "por_cop": 1 / 4000, "decimales": 2},
    "EUR": {"nombre": "Euro", "simbolo": "€", "por_cop": 1 / 4350, "decimales": 2},
}


def moneda_valida(codigo):
    return codigo if codigo in MONEDAS else MONEDA_BASE


def convertir(valor_cop, moneda):
    """Convierte un valor en COP a la moneda indicada (redondeado a sus decimales)."""
    datos = MONEDAS[moneda_valida(moneda)]
    return round(float(valor_cop) * datos["por_cop"], datos["decimales"])
