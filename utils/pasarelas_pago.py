import re
from abc import ABC, abstractmethod

from utils.sdk_pagos_externos import (
    StripeClient, StripeCardError, ClientePSE, NequiAPI, PayPalSDK, PayPalHttpError,
)


class ResultadoPago:
    def __init__(self, aprobado, mensaje, referencia=None):
        self.aprobado = aprobado
        self.mensaje = mensaje
        self.referencia = referencia


class PasarelaPago(ABC):
    """
    Interfaz OBJETIVO (target) que espera nuestro checkout.

    El checkout solo sabe llamar a procesar(monto, moneda, datos_formulario)
    y recibir un ResultadoPago en español. No sabe nada de Stripe, PSE,
    Nequi ni PayPal.

    Por seguridad, ningún dato de pago (número de tarjeta, CVV...) se
    guarda en la base de datos: solo la referencia de la transacción.
    """

    codigo = ""
    nombre = ""
    descripcion = ""
    monedas = ()          # monedas que acepta esta pasarela

    def acepta(self, moneda):
        return moneda in self.monedas

    def procesar(self, monto, moneda, datos):
        if not self.acepta(moneda):
            return ResultadoPago(False, f"{self.nombre} no acepta pagos en {moneda}.")
        return self._cobrar(monto, moneda, datos)

    @abstractmethod
    def _cobrar(self, monto, moneda, datos):
        raise NotImplementedError


# =====================================================================
# PATRÓN ADAPTER (traductor)
#
# Cada pasarela entrega una librería con su propia API (ver
# utils/sdk_pagos_externos.py) que no podemos cambiar. Cada adaptador
# implementa NUESTRA interfaz PasarelaPago y por dentro TRADUCE:
#   - de ida: los datos del formulario y el monto al formato que pide la
#     librería (centavos, códigos de banco, teléfono con +57, JSON...);
#   - de vuelta: la respuesta o el error de la librería a un ResultadoPago
#     con un mensaje en español.
# =====================================================================

class AdaptadorStripe(PasarelaPago):
    codigo = "tarjeta"
    nombre = "Tarjeta de crédito/débito"
    descripcion = "Visa, Mastercard, American Express (vía Stripe)"
    monedas = ("COP", "USD", "EUR")

    # Traducción de los códigos de error de Stripe (en inglés) a mensajes para el usuario.
    ERRORES = {
        "incorrect_number": "El número de tarjeta no es válido.",
        "missing_name": "Escribe el nombre del titular de la tarjeta.",
        "invalid_expiry": "La fecha de vencimiento debe tener el formato MM/AA.",
        "expired_card": "La tarjeta está vencida.",
        "incorrect_cvc": "El CVV debe tener 3 o 4 dígitos.",
        "insufficient_funds": "El banco rechazó el pago: fondos insuficientes.",
    }

    def __init__(self):
        self.cliente = StripeClient()   # el objeto adaptado

    def _cobrar(self, monto, moneda, datos):
        moneda_stripe = moneda.lower()
        centavos = round(monto) if moneda_stripe in StripeClient.ZERO_DECIMAL_CURRENCIES else round(monto * 100)
        vencimiento = re.fullmatch(r"\s*(\d{1,2})\s*/\s*(\d{2})\s*", datos.get("tarjeta_vencimiento", ""))
        tarjeta = {
            "number": re.sub(r"[\s-]", "", datos.get("tarjeta_numero", "")),
            "name": datos.get("tarjeta_titular", "").strip(),
            "exp_month": vencimiento.group(1) if vencimiento else None,
            "exp_year": 2000 + int(vencimiento.group(2)) if vencimiento else None,
            "cvc": datos.get("tarjeta_cvv", "").strip(),
        }
        try:
            cargo = self.cliente.charges_create(amount=centavos, currency=moneda_stripe, card=tarjeta)
        except StripeCardError as error:
            return ResultadoPago(False, self.ERRORES.get(error.code, "La tarjeta fue rechazada."))
        return ResultadoPago(True, "Pago aprobado con tarjeta.", cargo["id"].upper().replace("CH_", "TAR-"))


class AdaptadorPSE(PasarelaPago):
    codigo = "pse"
    nombre = "PSE"
    descripcion = "Débito desde tu cuenta bancaria"
    monedas = ("COP",)

    def __init__(self):
        self.cliente = ClientePSE()
        # El formulario muestra nombres de banco; PSE trabaja con códigos.
        self._codigo_por_banco = {nombre: codigo for codigo, nombre in ClientePSE.BANCOS.items()}

    @property
    def bancos(self):
        return list(self._codigo_por_banco)

    def _cobrar(self, monto, moneda, datos):
        codigo_banco = self._codigo_por_banco.get(datos.get("pse_banco", ""))
        if codigo_banco is None:
            return ResultadoPago(False, "Selecciona tu banco.")
        tipo_persona = "J" if datos.get("pse_tipo_persona") == "juridica" else "N"
        respuesta = self.cliente.crear_transaccion(
            valor_pesos=int(round(monto)), codigo_banco=codigo_banco,
            tipo_persona=tipo_persona, documento=datos.get("pse_documento", "").strip(),
        )
        if respuesta["estado"] != "OK":
            mensajes = {"DOCUMENTO_INVALIDO": "El documento debe tener entre 6 y 10 dígitos.",
                        "BANCO_INVALIDO": "Selecciona tu banco."}
            return ResultadoPago(False, mensajes.get(respuesta["codigo_error"], "PSE rechazó la transacción."))
        return ResultadoPago(True, f"Pago aprobado por PSE ({respuesta['banco']}).", f"PSE-{respuesta['CUS']}")


class AdaptadorNequi(PasarelaPago):
    codigo = "nequi"
    nombre = "Nequi"
    descripcion = "Paga desde la app con tu número de celular"
    monedas = ("COP",)

    def __init__(self):
        self.cliente = NequiAPI()

    def _cobrar(self, monto, moneda, datos):
        celular = re.sub(r"\D", "", datos.get("nequi_celular", ""))
        respuesta = self.cliente.unregistered_payment_request(
            phone_number=f"+57{celular}", value=str(int(round(monto))), reference="CloudMarket",
        )
        mensaje = respuesta["ResponseMessage"]
        if mensaje["ResponseHeader"]["Status"]["StatusCode"] != "0":
            return ResultadoPago(False, "El celular de Nequi debe tener 10 dígitos y empezar por 3.")
        return ResultadoPago(True, "Pago aprobado con Nequi.", "NEQ-" + mensaje["ResponseBody"]["any"]["transactionId"])


class AdaptadorPayPal(PasarelaPago):
    codigo = "paypal"
    nombre = "PayPal"
    descripcion = "Pagos internacionales en dólares o euros"
    monedas = ("USD", "EUR")

    def __init__(self):
        self.cliente = PayPalSDK()

    def _cobrar(self, monto, moneda, datos):
        orden = {
            "intent": "CAPTURE",
            "purchase_units": [{"amount": {"currency_code": moneda, "value": f"{monto:.2f}"}}],
            "payer": {"email_address": datos.get("paypal_correo", "").strip()},
        }
        try:
            respuesta = self.cliente.create_order(orden)
        except PayPalHttpError as error:
            mensajes = {"INVALID_PAYER_EMAIL": "Escribe el correo de tu cuenta PayPal.",
                        "CURRENCY_NOT_SUPPORTED": "PayPal no acepta esta moneda."}
            return ResultadoPago(False, mensajes.get(error.name, "PayPal rechazó el pago."))
        return ResultadoPago(True, "Pago aprobado con PayPal.", "PPL-" + respuesta["id"])


class PasarelaPagoFactory:
    """
    PATRÓN FACTORY METHOD

    El checkout pide una pasarela por su código ("tarjeta", "pse"...) y
    la fábrica decide qué adaptador instanciar. Para agregar una pasarela
    nueva basta con escribir su adaptador y registrarlo aquí.
    """

    _pasarelas = {p.codigo: p for p in (AdaptadorStripe, AdaptadorPSE, AdaptadorNequi, AdaptadorPayPal)}

    @classmethod
    def crear(cls, codigo):
        clase = cls._pasarelas.get(codigo)
        if clase is None:
            raise ValueError(f"Pasarela de pago desconocida: {codigo}")
        return clase()

    @classmethod
    def todas(cls):
        return [clase() for clase in cls._pasarelas.values()]

    @classmethod
    def disponibles(cls, moneda):
        return [p for p in cls.todas() if p.acepta(moneda)]
