"""
SIMULACIÓN de las librerías (SDK) que entregaría cada pasarela de pago.

Representan código de TERCEROS que no podemos modificar, y por eso cada
una tiene su propia forma de trabajar: nombres de métodos distintos,
inglés o español, montos en centavos o en pesos, códigos de respuesta
diferentes... Nuestra app no las usa directamente: las usa a través de
los adaptadores de utils/pasarelas_pago.py (patrón Adapter).

Ninguna hace cobros reales: solo validan los datos y responden como lo
haría el servicio real.
"""

import re
import secrets
from datetime import date


# ---------------------------------------------------------------------
# Stripe (tarjetas). API en inglés, montos en la unidad mínima de la
# moneda (centavos), errores con códigos en inglés.
# ---------------------------------------------------------------------
class StripeCardError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class StripeClient:
    ZERO_DECIMAL_CURRENCIES = {"cop"}        # el COP no usa centavos en Stripe
    DECLINED_TEST_CARD = "4000000000000002"  # tarjeta de prueba que siempre se rechaza

    @staticmethod
    def _luhn_ok(number):
        total = 0
        for i, digit in enumerate(reversed(number)):
            n = int(digit)
            if i % 2 == 1:
                n = n * 2 - 9 if n > 4 else n * 2
            total += n
        return total % 10 == 0

    def charges_create(self, amount, currency, card):
        """amount: entero en la unidad mínima (centavos). card: dict number/exp_month/exp_year/cvc/name."""
        number = card.get("number", "")
        if not number.isdigit() or not 13 <= len(number) <= 19 or not self._luhn_ok(number):
            raise StripeCardError("incorrect_number", "Your card number is incorrect.")
        if not card.get("name"):
            raise StripeCardError("missing_name", "Cardholder name is required.")
        try:
            month, year = int(card.get("exp_month")), int(card.get("exp_year"))
        except (TypeError, ValueError):
            raise StripeCardError("invalid_expiry", "Your card's expiration date is invalid.")
        today = date.today()
        if not 1 <= month <= 12:
            raise StripeCardError("invalid_expiry", "Your card's expiration month is invalid.")
        if (year, month) < (today.year, today.month):
            raise StripeCardError("expired_card", "Your card has expired.")
        if not re.fullmatch(r"\d{3,4}", card.get("cvc", "")):
            raise StripeCardError("incorrect_cvc", "Your card's security code is incorrect.")
        if number == self.DECLINED_TEST_CARD:
            raise StripeCardError("insufficient_funds", "Your card has insufficient funds.")
        return {"id": "ch_" + secrets.token_hex(8), "object": "charge", "amount": amount,
                "currency": currency, "status": "succeeded"}


# ---------------------------------------------------------------------
# PSE (ACH Colombia). API en español, valores en pesos enteros, bancos
# identificados por un código numérico y respuesta con estado + CUS.
# ---------------------------------------------------------------------
class ClientePSE:
    BANCOS = {"1007": "Bancolombia", "1001": "Banco de Bogotá", "1051": "Davivienda",
              "1013": "BBVA", "1023": "Banco de Occidente", "1002": "Banco Popular"}

    def crear_transaccion(self, valor_pesos, codigo_banco, tipo_persona, documento):
        if codigo_banco not in self.BANCOS:
            return {"estado": "FAILED", "codigo_error": "BANCO_INVALIDO", "CUS": None}
        if tipo_persona not in ("N", "J") or not re.fullmatch(r"\d{6,10}", documento):
            return {"estado": "FAILED", "codigo_error": "DOCUMENTO_INVALIDO", "CUS": None}
        return {"estado": "OK", "codigo_error": None, "CUS": str(secrets.randbelow(10**9)).zfill(9),
                "valor": valor_pesos, "banco": self.BANCOS[codigo_banco]}


# ---------------------------------------------------------------------
# Nequi. API en inglés, teléfono con indicativo, valor como texto y
# respuesta anidada con un código de estado ("0" = éxito).
# ---------------------------------------------------------------------
class NequiAPI:
    def unregistered_payment_request(self, phone_number, value, reference):
        if not re.fullmatch(r"\+573\d{9}", phone_number):
            return {"ResponseMessage": {"ResponseHeader": {"Status": {
                "StatusCode": "11-9L", "StatusDesc": "Invalid phone number"}}}}
        return {"ResponseMessage": {
            "ResponseHeader": {"Status": {"StatusCode": "0", "StatusDesc": "SUCCESS"}},
            "ResponseBody": {"any": {"transactionId": "NQ" + secrets.token_hex(6).upper(), "value": value}},
        }}


# ---------------------------------------------------------------------
# PayPal. Crea una "orden" con unidades de compra; el monto va como texto
# con 2 decimales y solo acepta ciertas monedas.
# ---------------------------------------------------------------------
class PayPalHttpError(Exception):
    def __init__(self, status_code, name):
        super().__init__(name)
        self.status_code = status_code
        self.name = name


class PayPalSDK:
    SUPPORTED_CURRENCIES = {"USD", "EUR"}

    def create_order(self, body):
        unit = body["purchase_units"][0]["amount"]
        if unit["currency_code"] not in self.SUPPORTED_CURRENCIES:
            raise PayPalHttpError(422, "CURRENCY_NOT_SUPPORTED")
        email = body.get("payer", {}).get("email_address", "")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise PayPalHttpError(400, "INVALID_PAYER_EMAIL")
        return {"id": secrets.token_hex(8).upper(), "status": "COMPLETED", "purchase_units": body["purchase_units"]}
