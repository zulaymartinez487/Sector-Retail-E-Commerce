import os
import pymysql
from dotenv import load_dotenv

load_dotenv()


class Database:
    

    _instancia = None
    _conexion = None

    def __new__(cls):
        if cls._instancia is None:
            cls._instancia = super(Database, cls).__new__(cls)
            cls._instancia._conectar()
        return cls._instancia

    def _conectar(self):
        """Abre la conexión hacia la base de datos usando los datos del .env"""
        try:
            self._conexion = pymysql.connect(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", 3306)),
                user=os.getenv("DB_USER", "root"),
                password=os.getenv("DB_PASSWORD", ""),
                database=os.getenv("DB_NAME", "bdaverd"),
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True,
            )
            print(" Conexión a la base de datos 'bdaverd' establecida correctamente.")
        except Exception as error:
            print(f" Error al conectar con la base de datos: {error}")
            self._conexion = None

    def obtener_conexion(self):
        """Devuelve la conexión activa, reconectando si hiciera falta."""
        if self._conexion is None or not self._conexion.open:
            self._conectar()
        return self._conexion

    def ejecutar_consulta(self, query, parametros=None, fetch=True):
        """
        Ejecuta una consulta SQL.
        - fetch=True  -> se usa para SELECT (devuelve filas).
        - fetch=False -> se usa para INSERT/UPDATE/DELETE (devuelve el id insertado).
        """
        conexion = self.obtener_conexion()
        if conexion is None:
            return None

        with conexion.cursor() as cursor:
            cursor.execute(query, parametros or ())
            if fetch:
                resultado = cursor.fetchall()
            else:
                conexion.commit()
                resultado = cursor.lastrowid

        return resultado
