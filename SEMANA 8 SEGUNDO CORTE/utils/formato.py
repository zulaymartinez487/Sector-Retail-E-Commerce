from utils.monedas import MONEDAS, convertir, moneda_valida


def formatear_precio(valor_cop, moneda="COP"):
    """
    Formatea un valor guardado en COP en la moneda indicada:
    249900 -> '$249.900' (COP), 'US$62,48' (USD), '€57,45' (EUR).
    """
    moneda = moneda_valida(moneda)
    datos = MONEDAS[moneda]
    valor = convertir(valor_cop, moneda)
    texto = f"{abs(valor):,.{datos['decimales']}f}"
    # Formato latino: punto para miles y coma para decimales.
    texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
    # Los descuentos se muestran como −$41.980 (signo antes del símbolo).
    return ("−" if valor < 0 else "") + datos["simbolo"] + texto
