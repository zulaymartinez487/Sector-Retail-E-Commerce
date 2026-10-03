from config.database import Database


class UsuarioModel:
    """
    MODELO (M de MVC)

    Se encarga únicamente de hablar con la base de datos.
    No sabe nada de HTML ni de rutas: solo maneja datos.
    """

    def __init__(self):
        # Database() siempre regresa la misma instancia gracias al Singleton
        self.db = Database()

    def buscar_por_correo(self, correo):
        query = "SELECT * FROM usuarios WHERE correo = %s LIMIT 1"
        resultado = self.db.ejecutar_consulta(query, (correo,))
        return resultado[0] if resultado else None

    def buscar_por_id(self, usuario_id):
        query = "SELECT * FROM usuarios WHERE id = %s LIMIT 1"
        resultado = self.db.ejecutar_consulta(query, (usuario_id,))
        return resultado[0] if resultado else None

    def crear_usuario(self, nombreCompleto, correo, contrasena_hash):
        query = """
            INSERT INTO usuarios (nombre, correo, contrasena)
            VALUES (%s, %s, %s)
        """
        return self.db.ejecutar_consulta(
            query, (nombreCompleto, correo, contrasena_hash), fetch=False
        )
