from datetime import datetime, timedelta
from config.database import Database

# Tiempo de vida del token en minutos
MINUTOS_EXPIRACION = 30


class RecuperacionModel:
    """
    MODELO (M de MVC)

    Maneja todo lo relacionado a los tokens de recuperación
    de contraseña: crearlos, validarlos y marcarlos como usados.
    """

    def __init__(self):
        self.db = Database()

    def crear_token(self, usuario_id, token):
        query = """
            INSERT INTO tokens_recuperacion (usuario_id, token, usado)
            VALUES (%s, %s, 0)
        """
        return self.db.ejecutar_consulta(query, (usuario_id, token), fetch=False)

    def buscar_token_valido(self, token):
        """
        Devuelve el registro del token solo si existe, no ha sido usado
        y no ha superado el tiempo de expiración.
        """
        query = """
            SELECT * FROM tokens_recuperacion
            WHERE token = %s AND usado = 0
            LIMIT 1
        """
        resultado = self.db.ejecutar_consulta(query, (token,))
        if not resultado:
            return None

        registro = resultado[0]
        expiracion = registro["fecha_creacion"] + timedelta(minutes=MINUTOS_EXPIRACION)

        if datetime.now() > expiracion:
            return None

        return registro

    def marcar_token_usado(self, token):
        query = "UPDATE tokens_recuperacion SET usado = 1 WHERE token = %s"
        return self.db.ejecutar_consulta(query, (token,), fetch=False)

    def actualizar_contrasena(self, usuario_id, contrasena_hash):
        query = "UPDATE usuarios SET contrasena = %s WHERE id = %s"
        return self.db.ejecutar_consulta(query, (contrasena_hash, usuario_id), fetch=False)
