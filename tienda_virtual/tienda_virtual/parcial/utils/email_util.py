import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def enviar_correo_recuperacion(destinatario, nombre, enlace):
    """
    Envía el correo con el enlace para restablecer la contraseña.
    Toma la configuración SMTP directamente del .env.

    Si el envío falla (por ejemplo, porque no se han configurado
    credenciales reales todavía), el enlace se imprime en consola
    para que puedas seguir probando el flujo sin bloquearte.
    """
    servidor = os.getenv("MAIL_SERVER")
    puerto = int(os.getenv("MAIL_PORT", 587))
    usar_tls = os.getenv("MAIL_USE_TLS", "True") == "True"
    usuario = os.getenv("MAIL_USERNAME")
    contrasena = os.getenv("MAIL_PASSWORD")
    remitente = os.getenv("MAIL_FROM", usuario)

    asunto = "Recuperación de contraseña - Tienda Virtual"
    cuerpo_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: auto;">
        <h2 style="color:#1e3c72;">Tienda Virtual</h2>
        <p>Hola {nombre},</p>
        <p>Recibimos una solicitud para restablecer tu contraseña. Haz clic en el siguiente botón:</p>
        <p style="text-align:center;">
            <a href="{enlace}"
               style="background:#1e3c72; color:#fff; padding:12px 20px;
                      border-radius:6px; text-decoration:none; display:inline-block;">
                Restablecer contraseña
            </a>
        </p>
        <p>Este enlace expira en 30 minutos. Si tú no solicitaste este cambio, puedes ignorar este correo.</p>
    </div>
    """

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
        print(f"✅ Correo de recuperación enviado a {destinatario}")
        return True
    except Exception as error:
        # Fallback para desarrollo/pruebas: si el correo no se pudo enviar
        # (credenciales no configuradas aún), se muestra el enlace en consola.
        print(f"⚠️  No se pudo enviar el correo ({error}). Enlace de prueba:")
        print(f"👉 {enlace}")
        return False
