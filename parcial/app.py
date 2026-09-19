import sys

# En Windows la consola suele usar cp1252, que no soporta los emojis que
# usamos en los print() de este proyecto (✅ ❌ 🚀 ...). Forzamos UTF-8
# aquí, antes de cualquier otro import, para que esos print() no revienten
# la app con un UnicodeEncodeError.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import os
from flask import Flask
from dotenv import load_dotenv

from controllers.auth_controller import auth_bp
from config.database import Database

load_dotenv()


def crear_app():
    app = Flask(__name__, template_folder="views", static_folder="static")
    app.secret_key = os.getenv("SECRET_KEY", "clave-secreta-por-defecto")
    app.register_blueprint(auth_bp)

    # Nombre de la marca centralizado en un solo lugar (.env -> APP_NAME).
    # Así todas las vistas usan {{ app_name }} en vez de tener el nombre
    # de la tienda repetido (hardcodeado) en cada archivo .html.
    @app.context_processor
    def inyectar_app_name():
        return {"app_name": os.getenv("APP_NAME", "CloudMarket")}

    return app


app = crear_app()

if __name__ == "__main__":
    # Al arrancar, se crea (o reutiliza) la única instancia de conexión (Singleton)
    Database()

    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", 5000))
    debug = os.getenv("APP_DEBUG", "True") == "True"

    print(f"🚀 Servidor corriendo en http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
