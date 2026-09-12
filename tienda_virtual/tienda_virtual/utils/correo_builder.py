class CorreoBuilder:
    """
    PATRÓN BUILDER

    Permite armar el cuerpo HTML de un correo paso a paso (encabezado,
    saludo, párrafos, botón, pie de página) en vez de escribir todo el
    HTML de una sola vez dentro de un f-string gigante.

    Cada método "con_..." agrega una pieza y devuelve el mismo builder
    (self), para poder encadenar las llamadas. Al final, construir()
    junta todas las piezas en el HTML final.
    """

    def __init__(self):
        self._partes = []

    def con_encabezado(self, titulo):
        self._partes.append(f'<h2 style="color:#1e3c72;">☁️ {titulo}</h2>')
        return self

    def con_saludo(self, nombre):
        self._partes.append(f"<p>Hola {nombre},</p>")
        return self

    def con_parrafo(self, texto):
        self._partes.append(f"<p>{texto}</p>")
        return self

    def con_boton(self, texto, url):
        self._partes.append(f"""
        <p style="text-align:center;">
            <a href="{url}"
               style="background:#1e3c72; color:#fff; padding:12px 20px;
                      border-radius:6px; text-decoration:none; display:inline-block;">
                {texto}
            </a>
        </p>
        """)
        return self

    def con_pie(self, texto="Este es un mensaje automático, por favor no respondas a este correo."):
        self._partes.append(f"""
        <hr style="border:none;border-top:1px solid #ddd;margin-top:20px;">
        <p style="font-size:12px;color:#888;">{texto}</p>
        """)
        return self

    def construir(self):
        """Devuelve el HTML final, ya armado con todas las piezas agregadas."""
        contenido = "".join(self._partes)
        return (
            f'<div style="font-family: Arial, sans-serif; max-width: 480px; margin: auto;">'
            f"{contenido}"
            f"</div>"
        )
