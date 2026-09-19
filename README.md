# Retail-E-Commerce

Proyecto de patrones de diseño de software: un login de tienda virtual
(Flask + MySQL) que implementa los 5 patrones creacionales — **Singleton**,
**Factory Method**, **Abstract Factory**, **Builder** y **Prototype**.

> La documentación detallada de cada patrón está en
> [`tienda_virtual/tienda_virtual/README.md SEMANA 5`](tienda_virtual/tienda_virtual/README.md%20SEMANA%205).
> Esta guía es solo para dejar el proyecto corriendo.

## 📂 ¿Dónde está el código?

El repo tiene una carpeta contenedora repetida por cómo se subió el
proyecto. El código que se ejecuta está dos niveles adentro:

```
Sector-Retail-E-Commerce/              <- carpeta donde clonaste el repo
└── tienda_virtual/
    └── tienda_virtual/                <- AQUÍ. app.py vive en esta carpeta.
        ├── app.py
        ├── requirements.txt
        ├── .env.example
        ├── config/
        ├── controllers/
        ├── models/
        ├── utils/
        ├── views/
        ├── static/
        └── database/bdaverd.sql
```

(La carpeta `SEMANA 5/` dentro de ahí es una copia histórica del código de
esa semana, no la que se ejecuta — no la uses para correr el proyecto.)

## ✅ Requisitos

- **Python 3.10+**
- **MySQL** corriendo (local o XAMPP/WAMP) — el login/registro no funciona
  sin esto, aunque el servidor sí arranca.
- (Opcional) una cuenta de Gmail con **contraseña de aplicación**, si quieres
  que los correos se envíen de verdad en vez de solo imprimirse en consola.

## 🚀 Pasos para correr el proyecto

1. **Clonar el repo y entrar a la carpeta del código:**
   ```bash
   git clone https://github.com/zulaymartinez487/Sector-Retail-E-Commerce.git
   cd Sector-Retail-E-Commerce/tienda_virtual/tienda_virtual
   ```

2. **Crear un entorno virtual e instalar dependencias:**
   ```bash
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Crear la base de datos** (con MySQL ya corriendo):
   ```bash
   mysql -u root -p < database/bdaverd.sql
   ```
   Esto crea la base `bdaverd` con sus tablas (`usuarios`,
   `tokens_recuperacion`).

4. **Configurar el `.env`** — copia la plantilla y edítala:
   ```bash
   cp .env.example .env       # Windows: copy .env.example .env
   ```
   Como mínimo, ajusta las credenciales de tu MySQL local:
   ```
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=tu_password_de_mysql
   DB_NAME=bdaverd
   ```
   El resto de valores (`APP_HOST`, `APP_PORT`, `APP_NAME`, `SECRET_KEY`)
   ya vienen con un default razonable para desarrollo local.

5. **(Opcional) Correo real vs. modo consola** — si dejas `MAIL_USERNAME` y
   `MAIL_PASSWORD` con los valores de ejemplo (`tu_correo@gmail.com` /
   `tu_contrasena_de_aplicacion`), la app detecta que no hay credenciales
   reales y usa automáticamente `NotificadorConsola`: los correos se
   imprimen en la terminal y en `logs/app.log` en vez de enviarse. Para que
   se envíen de verdad, pon un Gmail real y su
   [contraseña de aplicación](https://myaccount.google.com/apppasswords)
   (no tu contraseña normal) en `MAIL_USERNAME` / `MAIL_PASSWORD`.

6. **Ejecutar la aplicación:**
   ```bash
   python app.py
   ```
   Vas a ver algo así:
   ```
   Conexión a la base de datos 'bdaverd' establecida correctamente.
   🚀 Servidor corriendo en http://127.0.0.1:5000
   ```

7. **Abrir en el navegador:** [http://127.0.0.1:5000](http://127.0.0.1:5000)
   (redirige a `/login`). Desde ahí puedes ir a **Regístrate** para crear
   una cuenta nueva.

## 🩺 Problemas comunes

| Síntoma | Causa | Solución |
|---|---|---|
| `Error al conectar con la base de datos` al arrancar | MySQL no está corriendo, o las credenciales del `.env` están mal | Inicia MySQL (XAMPP/WAMP/servicio) y revisa `DB_USER`/`DB_PASSWORD` en `.env` |
| El registro/login no hace nada o falla | Mismo problema anterior — sin conexión a la BD, `usuario_model` no puede leer ni escribir | Confirma que `bdaverd` existe (`SHOW DATABASES;`) y que el script `database/bdaverd.sql` se ejecutó |
| `ModuleNotFoundError: No module named 'flask'` (o similar) | No activaste el entorno virtual o no corriste `pip install -r requirements.txt` | Activa el `venv` y reinstala dependencias |
| El correo no llega a la bandeja | Estás en modo consola (credenciales de ejemplo en `.env`), o el correo cayó en spam | Revisa la terminal/`logs/app.log` (ahí sale igual), o configura credenciales SMTP reales |
| `http://127.0.0.1:5000` no conecta desde el navegador | La app no llegó a arrancar (revisa la terminal por errores), o otro proceso ya está usando el puerto 5000 | Revisa la terminal donde corriste `python app.py`; cambia `APP_PORT` en `.env` si el puerto está ocupado |
| Quieres probar el registro pero tu correo ya está registrado | Los correos deben ser únicos en la tabla `usuarios` | Si usas Gmail, regístrate con `tunombre+prueba@gmail.com` — Gmail lo sigue entregando en tu misma bandeja, pero para la app es un correo distinto |
