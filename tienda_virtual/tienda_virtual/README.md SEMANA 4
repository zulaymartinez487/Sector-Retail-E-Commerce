# Tienda Virtual - Login (MVC + Singleton + Factory Method)

Proyecto en Python (Flask) que implementa un login para una tienda virtual,
usando el patrón de diseño **Modelo-Vista-Controlador (MVC)**, el patrón
**Singleton** para la conexión a la base de datos `bdaverd`, y el patrón
**Factory Method** en el envío de notificaciones de recuperación de
contraseña.

## 📂 Estructura del proyecto

```
tienda_virtual/
├── .env                     # Variables de entorno (host, puerto, BD, secret key)
├── .env.example             # Plantilla de ejemplo del .env
├── requirements.txt         # Dependencias del proyecto
├── app.py                   # Punto de entrada (arranca el servidor con host/puerto del .env)
├── config/
│   └── database.py          # Clase Database -> patrón SINGLETON
├── models/
│   └── usuario_model.py     # MODELO: acceso a datos de usuarios
├── controllers/
│   └── auth_controller.py   # CONTROLADOR: rutas de login, registro, logout
├── utils/
│   ├── notificador.py       # Notificador (interfaz) + NotificadorFactory -> FACTORY METHOD
│   └── logger.py            # Clase Logger -> patrón SINGLETON
├── views/
│   ├── login.html           # VISTA: formulario de inicio de sesión
│   ├── registro.html        # VISTA: formulario de registro
│   └── dashboard.html       # VISTA: panel tras iniciar sesión
├── static/css/style.css     # Estilos
└── database/bdaverd.sql     # Script para crear la base de datos y tablas
```

## ⚙️ Patrón Singleton

En `config/database.py`, la clase `Database` implementa el patrón Singleton:
sin importar cuántas veces se instancie `Database()` en el modelo o en la app,
siempre se reutiliza la **misma conexión** hacia la base de datos `bdaverd`.

```python
db1 = Database()
db2 = Database()
print(db1 is db2)  # True -> misma instancia
```

## 🏭 Patrón Factory Method

En `utils/notificador.py`, `NotificadorFactory.crear_notificador()` decide en
tiempo de ejecución **qué clase concreta** de `Notificador` instanciar, sin
que el controlador (`auth_controller.py`) tenga que conocerlas:

- `NotificadorEmail` — envía el correo real por SMTP (si hay credenciales
  configuradas en el `.env`).
- `NotificadorConsola` — si no hay credenciales SMTP configuradas, imprime
  y registra el enlace en el log, para poder seguir probando el flujo.

```python
notificador = NotificadorFactory.crear_notificador()  # decide la clase concreta
notificador.enviar(correo, nombre, enlace)             # el controlador solo usa la interfaz
```

## 🚀 Instalación y ejecución

1. Crear un entorno virtual (opcional pero recomendado):
   ```bash
   python -m venv venv
   source venv/bin/activate   # En Windows: venv\Scripts\activate
   ```

2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Crear la base de datos ejecutando el script SQL en tu gestor (MySQL):
   ```bash
   mysql -u root -p < database/bdaverd.sql
   ```

4. Ajustar el archivo `.env` con tus credenciales reales de la base de datos
   y la IP/puerto donde quieres correr la app:
   ```
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=tu_password
   DB_NAME=bdaverd

   APP_HOST=0.0.0.0
   APP_PORT=5000
   ```

5. Ejecutar la aplicación:
   ```bash
   python app.py
   ```

6. Abrir en el navegador la URL que se muestra en consola, por ejemplo:
   ```
   http://127.0.0.1:5000
   ```

## 🔑 Flujo del login

- `/registro` — crea un nuevo usuario (contraseña guardada con hash, nunca en texto plano).
- `/login` — valida el correo y la contraseña contra la base de datos.
- `/dashboard` — panel protegido, solo accesible si hay sesión activa.
- `/logout` — cierra la sesión.

## 🔁 Recuperación de contraseña

- `/recuperar-contrasena` — el usuario ingresa su correo. Si existe, se genera
  un token único (`secrets.token_urlsafe`) guardado en la tabla
  `tokens_recuperacion`, con una validez de **30 minutos**.
- Se envía un correo (vía SMTP, configurado en `.env`) con el enlace de
  restablecimiento. Si el envío falla (por ejemplo, no configuraste las
  credenciales SMTP todavía), el enlace se imprime en la consola del
  servidor para que puedas seguir probando el flujo.
- `/restablecer-contrasena/<token>` — valida que el token exista, no esté
  usado y no haya expirado; permite definir la nueva contraseña (se guarda
  con hash) y marca el token como usado para que no se pueda reutilizar.

### Configurar el envío de correos (Gmail como ejemplo)

En el `.env`:
```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu_correo@gmail.com
MAIL_PASSWORD=tu_contrasena_de_aplicacion
MAIL_FROM=Tienda Virtual <tu_correo@gmail.com>
APP_URL_BASE=http://127.0.0.1:5000
```
> En Gmail, `MAIL_PASSWORD` debe ser una "contraseña de aplicación", no la
> contraseña normal de la cuenta (Google la exige por seguridad).

## 📝 Notas

- Cambia `SECRET_KEY` en el `.env` por una clave segura antes de usar en producción.
- Para correr en otra IP de tu red local, cambia `APP_HOST` en el `.env` a `0.0.0.0`
  y accede desde otro equipo usando la IP de tu máquina.
