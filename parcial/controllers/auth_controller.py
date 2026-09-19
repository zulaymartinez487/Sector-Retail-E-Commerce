import os
import secrets
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from models.usuario_model import UsuarioModel
from models.recuperacion_model import RecuperacionModel
from utils.notificador import NotificadorFactory
from utils.logger import Logger

# CONTROLADOR (C de MVC)
# Recibe las peticiones, habla con el Modelo y decide qué Vista mostrar.

auth_bp = Blueprint("auth", __name__)
usuario_model = UsuarioModel()
recuperacion_model = RecuperacionModel()
logger = Logger()


@auth_bp.route("/")
def index():
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form.get("correo", "").strip()
        contrasena = request.form.get("contrasena", "").strip()

        if not correo or not contrasena:
            logger.warning("Login rechazado: faltan campos en el formulario.")
            flash("Por favor completa todos los campos.", "error")
            return render_template("login.html")

        usuario = usuario_model.buscar_por_correo(correo)

        if usuario and check_password_hash(usuario["contrasena"], contrasena):
            session["usuario_id"] = usuario["id"]
            session["usuario_nombre"] = usuario["nombre"]
            logger.info(f"Login exitoso para el usuario '{usuario['nombre']}' ({correo}).")

            notificador = NotificadorFactory.crear_notificador()
            notificador.enviar_alerta_login(usuario["correo"], usuario["nombre"])

            flash(f"¡Bienvenido, {usuario['nombre']}!", "success")
            return redirect(url_for("auth.dashboard"))
        else:
            logger.warning(f"Intento de login fallido para el correo '{correo}'.")
            flash("Correo o contraseña incorrectos.", "error")

    return render_template("login.html")


@auth_bp.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip()
        contrasena = request.form.get("contrasena", "").strip()

        if not nombre or not correo or not contrasena:
            flash("Todos los campos son obligatorios.", "error")
            return render_template("registro.html")

        if usuario_model.buscar_por_correo(correo):
            flash("Ese correo ya está registrado.", "error")
            return render_template("registro.html")

        hash_contrasena = generate_password_hash(contrasena)
        usuario_model.crear_usuario(nombre, correo, hash_contrasena)
        logger.info(f"Nuevo usuario registrado: '{nombre}' ({correo}).")

        notificador = NotificadorFactory.crear_notificador()
        notificador.enviar_bienvenida(correo, nombre)

        flash("Cuenta creada correctamente. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("auth.login"))

    return render_template("registro.html")


@auth_bp.route("/dashboard")
def dashboard():
    if "usuario_id" not in session:
        flash("Debes iniciar sesión primero.", "error")
        return redirect(url_for("auth.login"))
    return render_template("dashboard.html", nombre=session.get("usuario_nombre"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/recuperar-contrasena", methods=["GET", "POST"])
def recuperar_contrasena():
    """Paso 1: el usuario pide el enlace de recuperación con su correo."""
    if request.method == "POST":
        correo = request.form.get("correo", "").strip()
        usuario = usuario_model.buscar_por_correo(correo)

        # Por seguridad, siempre mostramos el mismo mensaje exista o no
        # el correo, para no revelar qué correos están registrados.
        if usuario:
            token = secrets.token_urlsafe(32)
            recuperacion_model.crear_token(usuario["id"], token)

            url_base = os.getenv("APP_URL_BASE", request.url_root.rstrip("/"))
            enlace = f"{url_base}/restablecer-contrasena/{token}"

            notificador = NotificadorFactory.crear_notificador()
            notificador.enviar_recuperacion(usuario["correo"], usuario["nombre"], enlace)
            logger.info(f"Solicitud de recuperación de contraseña para '{correo}': enlace generado y enviado.")
        else:
            logger.warning(f"Solicitud de recuperación para un correo no registrado: '{correo}'.")

        flash(
            "Si el correo está registrado, te enviamos un enlace para restablecer tu contraseña.",
            "success",
        )
        return redirect(url_for("auth.login"))

    return render_template("recuperar.html")


@auth_bp.route("/restablecer-contrasena/<token>", methods=["GET", "POST"])
def restablecer_contrasena(token):
    """Paso 2: el usuario define su nueva contraseña usando el token del correo."""
    registro_token = recuperacion_model.buscar_token_valido(token)

    if not registro_token:
        logger.warning(f"Intento de restablecimiento con un token inválido o expirado: '{token}'.")
        flash("El enlace de recuperación no es válido o ya expiró.", "error")
        return redirect(url_for("auth.recuperar_contrasena"))

    if request.method == "POST":
        contrasena = request.form.get("contrasena", "").strip()
        confirmar = request.form.get("confirmar_contrasena", "").strip()

        if not contrasena or not confirmar:
            logger.warning("Restablecimiento rechazado: faltan campos en el formulario.")
            flash("Completa ambos campos.", "error")
            return render_template("restablecer.html", token=token)

        if contrasena != confirmar:
            logger.warning("Restablecimiento rechazado: las contraseñas no coinciden.")
            flash("Las contraseñas no coinciden.", "error")
            return render_template("restablecer.html", token=token)

        hash_contrasena = generate_password_hash(contrasena)
        recuperacion_model.actualizar_contrasena(registro_token["usuario_id"], hash_contrasena)
        recuperacion_model.marcar_token_usado(token)
        logger.info(f"Contraseña restablecida correctamente para el usuario id={registro_token['usuario_id']}.")

        usuario = usuario_model.buscar_por_id(registro_token["usuario_id"])
        if usuario:
            notificador = NotificadorFactory.crear_notificador()
            notificador.enviar_confirmacion_restablecimiento(usuario["correo"], usuario["nombre"])

        flash("Tu contraseña se actualizó correctamente. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("auth.login"))

    return render_template("restablecer.html", token=token)
