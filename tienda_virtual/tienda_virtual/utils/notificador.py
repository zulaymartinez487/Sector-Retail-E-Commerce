import os
import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from utils.correo_builder import CorreoBuilder
from utils.logger import Logger

logger = Logger()

# Nombre de la marca centralizado en el .env (APP_NAME), igual que en app.py,
# para que los correos usen siempre el mismo nombre que se ve en las vistas.
NOMBRE_APP = os.getenv("APP_NAME", "CloudMarket")


class Notificador(ABC):
    """
    Interfaz común para cualquier forma de avisarle al usuario los
    eventos importantes de su cuenta (correo real, consola/log, y en
    el futuro SMS, push, etc. si se agregan nuevas subclases).
    """

    @abstractmethod
    def enviar_bienvenida(self, destinatario, nombre):
        """Se envía justo después de que el usuario se registra."""
        raise NotImplementedError

    @abstractmethod
    def enviar_alerta_login(self, destinatario, nombre):
        """Se envía cada vez que el usuario inicia sesión correctamente."""
        raise NotImplementedError

    @abstractmethod
    def enviar_recuperacion(self, destinatario, nombre, enlace):
        """Se envía con el enlace para restablecer la contraseña."""
        raise NotImplementedError

    @abstractmethod
    def enviar_confirmacion_restablecimiento(self, destinatario, nombre):
        """Se envía después de que el usuario define una contraseña nueva."""
        raise NotImplementedError


class NotificadorEmail(Notificador):
    """Envía cada notificación por correo electrónico real (SMTP)."""

    def _enviar_correo(self, destinatario, asunto, cuerpo_html):
        """Helper interno: arma y manda el correo. Lo reutilizan todos los métodos públicos."""
        servidor = os.getenv("MAIL_SERVER")
        puerto = int(os.getenv("MAIL_PORT", 587))
        usar_tls = os.getenv("MAIL_USE_TLS", "True") == "True"
        usuario = os.getenv("MAIL_USERNAME")
        contrasena = os.getenv("MAIL_PASSWORD")
        remitente = os.getenv("MAIL_FROM", usuario)

        mensaje = MIMEMultipart("alternative")
        mensaje["Subject"] = asunto
        mensaje["From"] = remitente
        mensaje["To"] = destinatario
        mensaje.attach(MIMEText(cuerpo_html, "html"))

        try:
            with smtplib.SMTP(servidor, puerto) as server:
                if usar_tls:
                    server.starttls()
                server.login(usuario, contrasena)
                server.sendmail(usuario, destinatario, mensaje.as_string())
            logger.info(f"Correo '{asunto}' enviado a {destinatario}")
            return True
        except Exception as error:
            logger.error(f"No se pudo enviar el correo '{asunto}' a {destinatario}: {error}")
            print(f"  No se pudo enviar el correo ({error}).")
            return False

    def enviar_bienvenida(self, destinatario, nombre):
        cuerpo_html = (
            CorreoBuilder()
            .con_encabezado(NOMBRE_APP)
            .con_saludo(nombre)
            .con_parrafo("Tu cuenta se creó correctamente. Ya puedes iniciar sesión y comenzar a comprar.")
            .con_pie()
            .construir()
        )
        return self._enviar_correo(destinatario, f"¡Bienvenido a {NOMBRE_APP}!", cuerpo_html)

    def enviar_alerta_login(self, destinatario, nombre):
        cuerpo_html = (
            CorreoBuilder()
            .con_encabezado(NOMBRE_APP)
            .con_saludo(nombre)
            .con_parrafo("Detectamos un inicio de sesión en tu cuenta. Si fuiste tú, no necesitas hacer nada.")
            .con_parrafo("Si no reconoces esta actividad, te recomendamos restablecer tu contraseña de inmediato.")
            .con_pie()
            .construir()
        )
        return self._enviar_correo(destinatario, f"Nuevo inicio de sesión - {NOMBRE_APP}", cuerpo_html)

    def enviar_recuperacion(self, destinatario, nombre, enlace):
        cuerpo_html = (
            CorreoBuilder()
            .con_encabezado(NOMBRE_APP)
            .con_saludo(nombre)
            .con_parrafo("Recibimos una solicitud para restablecer tu contraseña. Haz clic en el siguiente botón:")
            .con_boton("Restablecer contraseña", enlace)
            .con_parrafo("Este enlace expira en 30 minutos. Si tú no solicitaste este cambio, puedes ignorar este correo.")
            .con_pie()
            .construir()
        )
        return self._enviar_correo(destinatario, f"Recuperación de contraseña - {NOMBRE_APP}", cuerpo_html)

    def enviar_confirmacion_restablecimiento(self, destinatario, nombre):
        cuerpo_html = (
            CorreoBuilder()
            .con_encabezado(NOMBRE_APP)
            .con_saludo(nombre)
            .con_parrafo("Tu contraseña se actualizó correctamente. Ya puedes iniciar sesión con la nueva contraseña.")
            .con_parrafo("Si tú no hiciste este cambio, contacta al soporte de inmediato.")
            .con_pie()
            .construir()
        )
        return self._enviar_correo(destinatario, f"Contraseña actualizada - {NOMBRE_APP}", cuerpo_html)


class NotificadorConsola(Notificador):
    """
    Fallback para desarrollo: en vez de enviar un correo real,
    registra el evento en el log y lo imprime en la consola del
    servidor, para poder seguir probando el flujo sin credenciales SMTP.
    """

    def _registrar(self, mensaje):
        logger.info(f"[MODO CONSOLA] {mensaje}")
        print(f"👉 {mensaje}")
        return True

    def enviar_bienvenida(self, destinatario, nombre):
        return self._registrar(f"Bienvenida enviada a {nombre} ({destinatario}).")

    def enviar_alerta_login(self, destinatario, nombre):
        return self._registrar(f"Alerta de login enviada a {nombre} ({destinatario}).")

    def enviar_recuperacion(self, destinatario, nombre, enlace):
        return self._registrar(f"Enlace de recuperación para {nombre} ({destinatario}): {enlace}")

    def enviar_confirmacion_restablecimiento(self, destinatario, nombre):
        return self._registrar(f"Confirmación de restablecimiento enviada a {nombre} ({destinatario}).")


class NotificadorFactory:
    """
    PATRÓN FACTORY METHOD

    Concentra en un solo lugar la decisión de qué Notificador concreto
    usar, según la configuración disponible. El controlador que llama
    a crear_notificador() no necesita conocer las clases concretas
    (NotificadorEmail, NotificadorConsola): solo pide "un notificador"
    y usa sus métodos (enviar_bienvenida, enviar_alerta_login, etc.).
    """

    @staticmethod
    def crear_notificador():
        usuario = os.getenv("MAIL_USERNAME", "")
        contrasena = os.getenv("MAIL_PASSWORD", "")

        credenciales_configuradas = (
            usuario
            and contrasena
            and usuario != "tu_correo@gmail.com"
            and contrasena != "tu_contrasena_de_aplicacion"
        )

        if credenciales_configuradas:
            return NotificadorEmail()
        return NotificadorConsola()
