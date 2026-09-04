import logging
import os


class Logger:
    

    _instancia = None

    def __new__(cls):
        if cls._instancia is None:
            cls._instancia = super(Logger, cls).__new__(cls)
            cls._instancia._configurar()
        return cls._instancia

    def _configurar(self):
        """Configura el logger una única vez (handlers de archivo y consola)."""
        carpeta_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        carpeta_logs = os.path.join(carpeta_raiz, "logs")
        os.makedirs(carpeta_logs, exist_ok=True)
        ruta_archivo = os.path.join(carpeta_logs, "app.log")

        self._logger = logging.getLogger("tienda_virtual")
        self._logger.setLevel(logging.INFO)

        # Evita agregar handlers duplicados si Logger() se llama varias veces
        # (aunque el Singleton ya lo evita, esto protege contra recargas del
        # servidor en modo debug de Flask).
        if not self._logger.handlers:
            formato = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            handler_archivo = logging.FileHandler(ruta_archivo, encoding="utf-8")
            handler_archivo.setFormatter(formato)
            self._logger.addHandler(handler_archivo)

            handler_consola = logging.StreamHandler()
            handler_consola.setFormatter(formato)
            self._logger.addHandler(handler_consola)

    def info(self, mensaje):
        self._logger.info(mensaje)

    def warning(self, mensaje):
        self._logger.warning(mensaje)

    def error(self, mensaje):
        self._logger.error(mensaje)

    def debug(self, mensaje):
        self._logger.debug(mensaje)
