from abc import ABC, abstractmethod

# =====================================================================
# PATRÓN DECORATOR (capas)
#
# El total de un pedido se arma por capas que el comprador elige al
# pagar. El componente base es "productos + envío", y cada decorador
# ENVUELVE al anterior y le agrega (o le resta) algo:
#
#   CuponDescuento( SeguroEnvio( EmpaqueRegalo( CostoBase ) ) )
#
# Todos cumplen la misma interfaz (total() y desglose()), así que el
# checkout no sabe cuántas capas hay: solo le pide el total al objeto de
# afuera. Agregar un cargo nuevo es escribir otro decorador, sin tocar
# los existentes ni crear una clase por cada combinación de extras.
# =====================================================================


class CostoPedido(ABC):
    @abstractmethod
    def total(self):
        raise NotImplementedError

    @abstractmethod
    def desglose(self):
        """Lista de (concepto, valor) que explica cómo se llegó al total."""
        raise NotImplementedError


class CostoBase(CostoPedido):
    """Componente concreto: lo que cuestan los productos y los envíos."""

    def __init__(self, subtotal, envio):
        self.subtotal = subtotal
        self.envio = envio

    def total(self):
        return self.subtotal + self.envio

    def desglose(self):
        return [("Productos", self.subtotal), ("Envíos", self.envio)]


class DecoradorCosto(CostoPedido):
    """Decorador base: guarda el componente envuelto y por defecto le delega todo."""

    def __init__(self, componente):
        self.componente = componente

    @property
    def subtotal(self):
        return self.componente.subtotal

    @property
    def envio(self):
        return self.componente.envio

    def total(self):
        return self.componente.total()

    def desglose(self):
        return self.componente.desglose()


class EmpaqueRegalo(DecoradorCosto):
    PRECIO = 8000

    def total(self):
        return self.componente.total() + self.PRECIO

    def desglose(self):
        return self.componente.desglose() + [("🎁 Empaque de regalo", self.PRECIO)]


class SeguroEnvio(DecoradorCosto):
    """Asegura el valor de los productos contra pérdida o daño: 2 % del subtotal (mínimo $3.000)."""
    PORCENTAJE = 0.02
    MINIMO = 3000

    def _valor(self):
        return max(round(self.subtotal * self.PORCENTAJE), self.MINIMO)

    def total(self):
        return self.componente.total() + self._valor()

    def desglose(self):
        return self.componente.desglose() + [("🛡️ Seguro de envío (2 %)", self._valor())]


class CuponDescuento(DecoradorCosto):
    """Resta un descuento según el código del cupón."""

    CUPONES = {
        "BIENVENIDA10": ("10 % en productos (máx. $50.000)", lambda c: min(round(c.subtotal * 0.10), 50000)),
        "ENVIOGRATIS": ("Envíos gratis", lambda c: c.envio),
    }

    def __init__(self, componente, codigo):
        super().__init__(componente)
        self.codigo = codigo
        self.descripcion, self._calcular = self.CUPONES[codigo]

    def _valor(self):
        return self._calcular(self)

    def total(self):
        return max(self.componente.total() - self._valor(), 0)

    def desglose(self):
        return self.componente.desglose() + [(f"🏷️ Cupón {self.codigo}: {self.descripcion}", -self._valor())]

    @classmethod
    def es_valido(cls, codigo):
        return codigo in cls.CUPONES


def calcular_costo(subtotal, envio, regalo=False, seguro=False, cupon=None):
    """Arma el costo del pedido apilando solo las capas que eligió el comprador."""
    costo = CostoBase(subtotal, envio)
    if regalo:
        costo = EmpaqueRegalo(costo)
    if seguro:
        costo = SeguroEnvio(costo)
    if cupon:
        costo = CuponDescuento(costo, cupon)
    return costo
