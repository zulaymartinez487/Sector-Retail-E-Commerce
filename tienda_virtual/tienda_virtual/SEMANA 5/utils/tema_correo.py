from abc import ABC, abstractmethod


class TemaCorreoFactory(ABC):
    """
    PATRÓN ABSTRACT FACTORY

    Crea una FAMILIA de piezas visuales (color + ícono) que deben
    combinarse entre sí. Cada fábrica concreta garantiza que esas piezas
    sean coherentes: nunca se mezcla, por ejemplo, un color de alerta
    con el ícono neutro de un correo informativo.

    A diferencia del Factory Method de NotificadorFactory (que elige
    ENTRE canales distintos: correo real o consola), esta fábrica no
    elige entre alternativas sueltas, sino que arma un conjunto de
    productos relacionados para un mismo tema visual.
    """

    @abstractmethod
    def crear_color(self):
        raise NotImplementedError

    @abstractmethod
    def crear_icono(self):
        raise NotImplementedError


class TemaEstandarFactory(TemaCorreoFactory):
    """Familia visual para correos informativos: bienvenida, confirmaciones."""

    def crear_color(self):
        return "#1e3c72"

    def crear_icono(self):
        return "☁️"


class TemaSeguridadFactory(TemaCorreoFactory):
    """Familia visual para correos sensibles: alerta de login, recuperación."""

    def crear_color(self):
        return "#b3401f"

    def crear_icono(self):
        return "🔒"
