from utils.correo_builder import CorreoBuilder


class RegistroPlantillasCorreo:
    """
    PATRÓN PROTOTYPE

    Todos los correos de un mismo tema (ver utils/tema_correo.py)
    empiezan con el mismo encabezado: mismo título, mismo color, mismo
    ícono. En vez de reconstruir esa parte fija cada vez que se envía
    un correo, este registro arma UN solo CorreoBuilder "prototipo" por
    cada combinación (titulo, color, icono) y, para cada correo nuevo,
    lo clona (CorreoBuilder.clonar()) en vez de volver a llamar
    con_encabezado(). Los correos "bienvenida" y "confirmación de
    restablecimiento" comparten el mismo tema, así que reutilizan y
    clonan exactamente el mismo prototipo.
    """

    _prototipos = {}

    @classmethod
    def obtener_encabezado(cls, titulo, color, icono):
        clave = (titulo, color, icono)
        if clave not in cls._prototipos:
            cls._prototipos[clave] = CorreoBuilder().con_encabezado(
                titulo, color=color, icono=icono
            )
        return cls._prototipos[clave].clonar()
