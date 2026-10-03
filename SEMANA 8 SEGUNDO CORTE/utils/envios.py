import random
import string
from abc import ABC, abstractmethod

# =====================================================================
# PATRÓN BRIDGE (puente)
#
# Un envío varía en DOS dimensiones independientes:
#   - la MODALIDAD que elige el comprador: estándar o express
#     (define las reglas: cuánto se cobra, cuántos días tarda, si aplica
#     envío gratis), y
#   - la TRANSPORTADORA con la que despacha cada tienda: Servientrega,
#     Coordinadora, Interrapidísimo, Envía...
#     (define la tarifa base, sus tiempos y el formato de su número de guía).
#
# Con herencia habría que crear una clase por combinación
# (EstandarServientrega, ExpressServientrega, EstandarCoordinadora...):
# 2 modalidades x 4 transportadoras = 8 clases, y cada transportadora
# nueva sumaría 2 más. El puente separa las dos jerarquías: la modalidad
# (abstracción) TIENE una transportadora (implementación) y le delega lo
# que depende de ella. Así se combinan libremente: 2 + 4 clases.
# =====================================================================


# ---------- Implementación: transportadoras ----------

class Transportadora(ABC):
    nombre = ""
    tarifa_base = 0         # COP por paquete
    dias_base = 0           # días hábiles de entrega en servicio normal

    @abstractmethod
    def generar_guia(self):
        """Cada transportadora tiene su propio formato de número de guía."""
        raise NotImplementedError


class Servientrega(Transportadora):
    nombre = "Servientrega"
    tarifa_base = 12000
    dias_base = 3

    def generar_guia(self):
        return "".join(random.choices(string.digits, k=10))


class Coordinadora(Transportadora):
    nombre = "Coordinadora"
    tarifa_base = 11000
    dias_base = 4

    def generar_guia(self):
        return "CO" + "".join(random.choices(string.digits, k=11))


class Interrapidisimo(Transportadora):
    nombre = "Interrapidísimo"
    tarifa_base = 10500
    dias_base = 4

    def generar_guia(self):
        return "IR-" + "".join(random.choices(string.digits, k=9))


class Envia(Transportadora):
    nombre = "Envía"
    tarifa_base = 9500
    dias_base = 5

    def generar_guia(self):
        return "ENV" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


TRANSPORTADORAS = {t.nombre: t for t in (Servientrega, Coordinadora, Interrapidisimo, Envia)}


def crear_transportadora(nombre):
    return TRANSPORTADORAS.get(nombre, Servientrega)()


# ---------- Abstracción: modalidades de envío ----------

class ModalidadEnvio(ABC):
    codigo = ""
    nombre = ""

    def __init__(self, transportadora):
        # El "puente": la modalidad guarda una transportadora y le delega
        # la tarifa, los tiempos y la guía.
        self.transportadora = transportadora

    @abstractmethod
    def costo(self, subtotal):
        raise NotImplementedError

    @abstractmethod
    def dias_entrega(self):
        """Devuelve (mínimo, máximo) de días hábiles."""
        raise NotImplementedError

    def generar_guia(self):
        return self.transportadora.generar_guia()

    def descripcion(self):
        minimo, maximo = self.dias_entrega()
        dias = f"{minimo} día hábil" if minimo == maximo == 1 else f"{minimo} a {maximo} días hábiles"
        return f"{self.nombre} con {self.transportadora.nombre} · {dias}"


class EnvioEstandar(ModalidadEnvio):
    codigo = "estandar"
    nombre = "Envío estándar"
    ENVIO_GRATIS_DESDE = 150000

    def costo(self, subtotal):
        return 0 if subtotal >= self.ENVIO_GRATIS_DESDE else self.transportadora.tarifa_base

    def dias_entrega(self):
        return self.transportadora.dias_base, self.transportadora.dias_base + 2


class EnvioExpress(ModalidadEnvio):
    codigo = "express"
    nombre = "Envío express"
    RECARGO = 8000

    def costo(self, subtotal):
        # El express nunca es gratis: cuesta la tarifa de la transportadora más un recargo.
        return self.transportadora.tarifa_base + self.RECARGO

    def dias_entrega(self):
        return 1, 2


MODALIDADES = {m.codigo: m for m in (EnvioEstandar, EnvioExpress)}


def crear_envio(modalidad, transportadora):
    """Une una modalidad con una transportadora: cualquier combinación es válida."""
    clase = MODALIDADES.get(modalidad, EnvioEstandar)
    return clase(crear_transportadora(transportadora))
