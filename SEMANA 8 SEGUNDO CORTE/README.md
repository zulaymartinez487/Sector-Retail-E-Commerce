# Retail-E-Commerce — Marketplace Multivendedor (MVC + patrones creacionales y estructurales)

Proyecto 7 del sector Retail/E-commerce: un **marketplace multivendedor**
en Python (Flask + MySQL). Varias tiendas venden en el mismo sitio y los
compradores pagan todo en un solo checkout. Está organizado con
**Modelo-Vista-Controlador (MVC)** e implementa cinco patrones
**creacionales** y cuatro **estructurales**.

### Patrones creacionales

| Patrón | Dónde | Para qué |
|---|---|---|
| **Singleton** | `config/database.py`, `utils/logger.py` | Una sola conexión a la BD y un solo logger |
| **Factory Method** | `utils/notificador.py`, `utils/pasarelas_pago.py` | Decidir cómo notificar (correo real o consola) y qué pasarela de pago instanciar (tarjeta, PSE, Nequi, PayPal) |
| **Abstract Factory** | `utils/tema_correo.py` | Familia de piezas visuales (color + ícono) de cada tipo de correo |
| **Builder** | `utils/correo_builder.py` | Construir el HTML de los correos paso a paso |
| **Prototype** | `utils/plantillas_correo.py` (+ `CorreoBuilder.clonar()`) | Clonar el encabezado ya armado de cada tema en vez de reconstruirlo |

### Patrones estructurales

| Patrón | Área | Dónde | Para qué |
|---|---|---|---|
| **Adapter** (traductor) | Medios de pago | `utils/pasarelas_pago.py` + `utils/sdk_pagos_externos.py` | Traducir la API propia de cada pasarela (Stripe, PSE, Nequi, PayPal) a una sola interfaz `PasarelaPago` |
| **Bridge** (arquitecto) | Envíos | `utils/envios.py` | Separar la **modalidad** de envío (estándar / express) de la **transportadora** (Servientrega, Coordinadora, Interrapidísimo, Envía) |
| **Composite** (árbol) | Catálogo e inventario | `models/categoria_model.py` | Tratar igual una categoría y un producto dentro del árbol del catálogo (conteos, stock y valor de inventario por rama) |
| **Decorator** (capas) | Pedidos | `utils/cargos_pedido.py` | Armar el total del pedido apilando capas opcionales: empaque de regalo, seguro de envío y cupones |

#### 🔌 Adapter — medios de pago

Cada pasarela entrega su propia librería, y no podemos cambiarla. En
`utils/sdk_pagos_externos.py` están simuladas tal como serían: Stripe
habla en inglés y cobra en centavos, PSE pide el **código** del banco y
responde con un `CUS`, Nequi quiere el celular con `+57` y responde con
códigos como `"11-9L"`, y PayPal recibe una orden JSON con el monto como
texto. Cada **adaptador** (`AdaptadorStripe`, `AdaptadorPSE`,
`AdaptadorNequi`, `AdaptadorPayPal`) implementa nuestra interfaz
`PasarelaPago` y traduce en los dos sentidos:

```python
pasarela = PasarelaPagoFactory.crear("tarjeta")      # Factory Method -> AdaptadorStripe
resultado = pasarela.procesar(72.95, "USD", datos)   # el checkout siempre llama igual
# Por dentro: 72.95 USD -> 7295 centavos; StripeCardError("insufficient_funds")
# -> ResultadoPago(False, "El banco rechazó el pago: fondos insuficientes.")
```

#### 🌉 Bridge — envíos

Un envío varía en dos dimensiones independientes. La **abstracción**
(`EnvioEstandar`, `EnvioExpress`) define las reglas: el estándar es
gratis desde $150.000 y el express cuesta la tarifa más $8.000 y llega en
1 a 2 días. La **implementación** (`Servientrega`, `Coordinadora`,
`Interrapidisimo`, `Envia`) pone la tarifa base, los días y el formato de
su número de guía. La modalidad *tiene* una transportadora (el puente), así
que 2 modalidades × 4 transportadoras salen con 6 clases en vez de 8, y
una transportadora nueva es solo una clase más.

```python
envio = crear_envio("express", "Coordinadora")   # cualquier combinación
envio.costo(200000)        # 11000 + 8000 = 19000
envio.generar_guia()       # "CO04812345678"  (formato de Coordinadora)
```

En la app: cada tienda elige su transportadora (al abrirla o desde su
panel), el comprador elige la modalidad en el checkout, y al marcar un
envío como *enviado* la transportadora genera la guía automáticamente.

#### 🌳 Composite — catálogo e inventario

Las categorías forman un árbol (tabla `categorias` con `padre_id`):
*Tecnología → Audio, Celulares...*, *Moda → Calzado, Ropa, Accesorios*...
`Categoria` (nodo compuesto) y `ProductoHoja` (hoja) cumplen la misma
interfaz `ComponenteCatalogo`, y cada categoría responde sumando a sus
hijos de forma recursiva:

```python
arbol = CategoriaModel().construir_arbol(productos)
arbol.buscar("Tecnología").contar_productos()    # 5 (todas sus subcategorías)
arbol.buscar("Audio").valor_inventario()         # precio x stock de sus productos
```

En la app: el menú de categorías del inicio muestra cuántos productos
hay en cada rama, filtrar por *Tecnología* incluye todas sus
subcategorías, las migas de pan salen de la ruta del nodo, y el vendedor
ve su **inventario por categoría** (productos, unidades y valor) en
*Catálogo e inventario*. Los productos solo se publican en categorías hoja.

#### 🎂 Decorator — pedidos

El total se arma por capas. El componente base es *productos + envíos* y
cada decorador envuelve al anterior:

```python
costo = CuponDescuento(SeguroEnvio(EmpaqueRegalo(CostoBase(subtotal, envio))), "BIENVENIDA10")
costo.total()       # suma/resta lo de cada capa
costo.desglose()    # una línea por capa, para mostrarla en el checkout
```

En la app: en el paso 1 del checkout el comprador elige empaque de
regalo (+$8.000), seguro de envío (2 % del valor, mínimo $3.000) y un
cupón (`BIENVENIDA10`: 10 % en productos hasta $50.000; `ENVIOGRATIS`). El
desglose se guarda con el pedido (`pedidos.cargos`) y se ve en *Mis pedidos*.

## 🛒 Requisitos del marketplace

| Requisito | Cómo se implementó |
|---|---|
| **Gestión de catálogo, inventario, pedidos y envíos** | Cualquier usuario abre su tienda en **Vender** (`/vendedor/registro`). En su panel publica productos con foto, edita precio y stock, los pausa, ve alertas de stock bajo y gestiona sus envíos (pendiente → preparando → enviado → entregado, con transportadora y número de guía). Un pedido con productos de varias tiendas se divide en **un envío por vendedor**, y cada tienda cobra su propio envío con su transportadora: estándar (gratis desde $150.000) o express (**Bridge**). Las categorías forman un árbol y el vendedor ve su inventario por categoría (**Composite**). Al pagar se pueden sumar empaque de regalo, seguro y cupones (**Decorator**). |
| **Múltiples gateways de pago y monedas** | `PasarelaPagoFactory` crea el **adaptador** (**Adapter**) de la pasarela elegida: **Tarjeta** (valida con el algoritmo de Luhn, vencimiento y CVV), **PSE** y **Nequi** (solo COP) y **PayPal** (solo USD/EUR). El usuario elige **COP, USD o EUR** en el encabezado y todos los precios se convierten. Si el pago es rechazado no se crea el pedido ni se descuenta el stock (transacción). Los pagos son **simulados**: no hay cobros reales ni se guardan datos de tarjetas. |

**Tarjetas de prueba:** `4242 4242 4242 4242` (aprobada) y
`4000 0000 0000 0002` (rechazada por fondos insuficientes), con cualquier
vencimiento futuro (ej. `12/30`) y CVV de 3 dígitos.

**Cuentas de demostración** (contraseña `demo123`), creadas por el script SQL:

| Rol | Correo |
|---|---|
| Vendedor de **TecnoHub** (tecnología) | `tecnohub@demo.com` |
| Vendedor de **Moda Urbana** | `modaurbana@demo.com` |
| Vendedor de **Casa Verde** (hogar y belleza) | `casaverde@demo.com` |
| Compradores con historial de compras | `comprador1@demo.com` … `comprador10@demo.com` |

## 📂 Estructura del proyecto

```
├── app.py                    # Punto de entrada (arranca el servidor con host/puerto del .env)
├── requirements.txt          # Dependencias
├── .env.example              # Plantilla del .env
├── config/
│   └── database.py           # Database -> SINGLETON
├── models/
│   ├── usuario_model.py      # MODELO: usuarios
│   ├── recuperacion_model.py # MODELO: tokens de recuperación de contraseña
│   ├── vendedor_model.py     # MODELO: tiendas, transportadora y estadísticas del vendedor
│   ├── categoria_model.py    # Árbol de categorías -> COMPOSITE
│   ├── producto_model.py     # MODELO: catálogo e inventario (por tienda)
│   ├── carrito_model.py      # MODELO: carrito en la sesión, agrupado por tienda + envíos
│   └── pedido_model.py       # MODELO: pedidos y envíos (transacción: stock + pago + pedido)
├── controllers/
│   ├── auth_controller.py    # CONTROLADOR: login, registro, logout, recuperación
│   ├── tienda_controller.py  # CONTROLADOR: catálogo, tiendas, carrito, checkout, pedidos
│   └── vendedor_controller.py# CONTROLADOR: abrir tienda, productos, inventario y envíos
├── utils/
│   ├── notificador.py        # Notificador + NotificadorFactory -> FACTORY METHOD
│   ├── pasarelas_pago.py     # Adaptadores de pago -> ADAPTER (+ PasarelaPagoFactory -> FACTORY METHOD)
│   ├── sdk_pagos_externos.py # Librerías simuladas de Stripe, PSE, Nequi y PayPal (lo que se adapta)
│   ├── envios.py             # Modalidad de envío x transportadora -> BRIDGE
│   ├── cargos_pedido.py      # Extras del pedido por capas -> DECORATOR
│   ├── monedas.py            # COP / USD / EUR y conversión
│   ├── tema_correo.py        # TemaCorreoFactory y sus fábricas concretas -> ABSTRACT FACTORY
│   ├── correo_builder.py     # CorreoBuilder -> BUILDER (+ clonar() -> PROTOTYPE)
│   ├── plantillas_correo.py  # RegistroPlantillasCorreo -> PROTOTYPE
│   ├── formato.py            # Formato de precios en la moneda elegida
│   └── logger.py             # Logger -> SINGLETON
├── views/
│   ├── login.html, registro.html, recuperar.html, restablecer.html
│   ├── tienda/               # inicio, producto, tienda pública, carrito, checkout, mis pedidos
│   └── vendedor/             # abrir tienda, panel, productos, formulario de producto, envíos
├── static/
│   ├── css/style.css         # Estilos del login/registro
│   ├── css/tienda.css        # Estilos del marketplace (responsive)
│   └── img/                  # Banner y fotos de los productos (y las que suben los vendedores)
├── database/bdaverd.sql      # Crea la BD, las tablas y carga tiendas, productos y datos demo
└── diagramas_uml/            # Diagramas UML y vistas previas de los correos
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

`utils/logger.py` aplica el mismo patrón para que toda la app escriba en un
único logger (`logs/app.log`).

## 🏭 Patrón Factory Method

En `utils/notificador.py`, `NotificadorFactory.crear_notificador()` decide en
tiempo de ejecución **qué clase concreta** de `Notificador` instanciar, sin
que el controlador (`auth_controller.py`) tenga que conocerlas:

- `NotificadorEmail` — envía el correo real por SMTP (si hay credenciales
  configuradas en el `.env`).
- `NotificadorConsola` — si no hay credenciales SMTP configuradas, imprime
  y registra el enlace en el log, para poder seguir probando el flujo.

```python
notificador = NotificadorFactory.crear_notificador()             # decide la clase concreta
notificador.enviar_recuperacion(correo, nombre, enlace)          # el controlador solo usa la interfaz
```

`Notificador` también expone `enviar_bienvenida()` (registro),
`enviar_alerta_login()` (login) y `enviar_confirmacion_restablecimiento()`
(tras restablecer la contraseña) — mismos dos "sabores" (`NotificadorEmail` /
`NotificadorConsola`) para cada evento de la cuenta.

## 🏛️ Patrón Abstract Factory

En `utils/tema_correo.py`, `TemaCorreoFactory` es una fábrica abstracta que
crea una **familia de piezas visuales relacionadas** (color + ícono) que
deben quedar siempre coherentes entre sí. A diferencia de
`NotificadorFactory` (que elige entre canales sueltos: correo o consola),
esta fábrica arma un conjunto de productos que van juntos:

- `TemaEstandarFactory` — azul `#1e3c72` + ☁️, para correos informativos
  (bienvenida, confirmación de restablecimiento).
- `TemaSeguridadFactory` — rojo `#b3401f` + 🔒, para correos sensibles
  (alerta de login, recuperación de contraseña).

```python
tema = TemaSeguridadFactory()             # fábrica concreta de la familia "seguridad"
color = tema.crear_color()                # "#b3401f"
icono = tema.crear_icono()                # "🔒"  -> color e ícono siempre van juntos
```

`NotificadorEmail` elige la fábrica según el tipo de correo y le pasa el
color/ícono resultante a `CorreoBuilder`.

## 🧱 Patrón Builder

En `utils/correo_builder.py`, `CorreoBuilder` arma el cuerpo HTML de cada
correo **paso a paso**, en vez de escribir todo el HTML de una sola vez en
un f-string gigante. Cada método `con_...` agrega una pieza y devuelve el
mismo builder (se pueden encadenar), y `construir()` entrega el HTML final:

```python
cuerpo_html = (
    CorreoBuilder()
    .con_encabezado("CloudMarket", color="#1e3c72", icono="☁️")
    .con_saludo("Zulay")
    .con_parrafo("Recibimos una solicitud para restablecer tu contraseña.")
    .con_boton("Restablecer contraseña", enlace, color="#1e3c72")
    .con_pie()
    .construir()
)
```

`NotificadorEmail` usa este builder en sus 4 métodos, cada uno combinando
las piezas que necesita. En vez de llamar `con_encabezado()` desde cero cada
vez, arranca desde el prototipo clonado que entrega `RegistroPlantillasCorreo`.

## 🧬 Patrón Prototype

En `utils/correo_builder.py`, `CorreoBuilder.clonar()` devuelve una copia
independiente del builder (con `copy.deepcopy` sobre sus piezas ya
agregadas). En `utils/plantillas_correo.py`, `RegistroPlantillasCorreo`
aprovecha eso: arma **una sola vez** un `CorreoBuilder` "prototipo" con el
encabezado ya puesto para cada combinación (título, color, ícono), lo guarda
en caché, y para cada correo nuevo entrega un **clon** de ese prototipo:

```python
builder = RegistroPlantillasCorreo.obtener_encabezado(
    "CloudMarket", "#1e3c72", "☁️"
)                                  # clon del prototipo (ya trae el encabezado)
builder.con_saludo("Zulay")       # se le agregan las piezas propias de este correo
```

Como `enviar_bienvenida()` y `enviar_confirmacion_restablecimiento()` usan el
mismo tema (`TemaEstandarFactory`), ambos reutilizan y clonan **el mismo**
prototipo cacheado en vez de construir el encabezado dos veces.

## ✅ Requisitos

- **Python 3.10+**
- **MySQL** corriendo (local o XAMPP/WAMP) — el login/registro no funciona
  sin esto, aunque el servidor sí arranca.
- (Opcional) una cuenta de Gmail con **contraseña de aplicación**, si quieres
  que los correos se envíen de verdad en vez de solo imprimirse en consola.

## 🚀 Pasos para correr el proyecto

1. **Clonar el repo y entrar a la carpeta de esta entrega:**
   ```bash
   git clone https://github.com/zulaymartinez487/Sector-Retail-E-Commerce.git
   cd "Sector-Retail-E-Commerce/SEMANA 8 SEGUNDO CORTE"
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
   `tokens_recuperacion`, `vendedores`, `categorias`, `productos`, `pedidos`,
   `pedido_detalle`, `envios`) y carga 3 tiendas, 14 productos con fotos
   y pedidos de ejemplo. Se puede ejecutar varias veces sin
   duplicar nada.

   > Si ya tenías la base de una versión anterior (sin marketplace), lo
   > más simple es borrarla y crearla de nuevo (pierdes los usuarios de
   > prueba): `DROP DATABASE bdaverd;` y vuelve a ejecutar el script.

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
   `MAIL_PASSWORD` con los valores de ejemplo, la app detecta que no hay
   credenciales reales y usa automáticamente `NotificadorConsola`: los
   correos se imprimen en la terminal y en `logs/app.log` en vez de
   enviarse. Para que se envíen de verdad, pon un Gmail real y su
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
   Primero verás el **login** (o puedes **registrarte**, o entrar con una
   de las cuentas demo). Después de iniciar sesión entras al marketplace;
   todas sus páginas exigen sesión.

## 🔑 Rutas

**Comprador**

- `/` — inicio: categorías, buscador (`?q=`, también busca por tienda),
  orden (`?orden=precio_asc|precio_desc`) y catálogo.
- `/producto/<id>` — detalle, tienda que lo vende y productos relacionados de la misma categoría.
- `/tienda/<id>` — página pública de una tienda con sus productos.
- `/moneda` — cambia la moneda (COP, USD o EUR).
- `/carrito` — carrito agrupado por tienda, con un envío por tienda.
- `/checkout` — datos de entrega y pago con la pasarela elegida.
- `/mis-pedidos` — pedidos con el seguimiento del envío de cada tienda.

**Vendedor** (`/vendedor/...`)

- `/vendedor/registro` — abrir una tienda.
- `/vendedor/` — panel: ventas, pedidos por despachar y stock bajo.
- `/vendedor/productos` — catálogo e inventario (publicar, editar, pausar).
- `/vendedor/productos/nuevo` y `/vendedor/productos/<id>/editar` — formulario con foto.
- `/vendedor/envios` — pedidos de la tienda; cambiar el estado y poner la guía.

**Cuenta**

- `/registro` — crea un nuevo usuario (contraseña guardada con hash).
- `/login` — valida el correo y la contraseña contra la base de datos.
- `/dashboard` — redirige a "Mis pedidos".
- `/logout` — cierra la sesión.
- `/recuperar-contrasena` — genera un token único (válido **30 minutos**) y
  envía el enlace de restablecimiento.
- `/restablecer-contrasena/<token>` — valida el token y permite definir la
  nueva contraseña; el token queda marcado como usado.

## 🩺 Problemas comunes

| Síntoma | Causa | Solución |
|---|---|---|
| `Error al conectar con la base de datos` al arrancar | MySQL no está corriendo, o las credenciales del `.env` están mal | Inicia MySQL (XAMPP/WAMP/servicio) y revisa `DB_USER`/`DB_PASSWORD` en `.env` |
| El registro/login no hace nada o falla | Sin conexión a la BD, `usuario_model` no puede leer ni escribir | Confirma que `bdaverd` existe (`SHOW DATABASES;`) y que el script `database/bdaverd.sql` se ejecutó |
| `ModuleNotFoundError: No module named 'flask'` (o similar) | No activaste el entorno virtual o no corriste `pip install -r requirements.txt` | Activa el `venv` y reinstala dependencias |
| El correo no llega a la bandeja | Estás en modo consola (credenciales de ejemplo en `.env`), o el correo cayó en spam | Revisa la terminal/`logs/app.log`, o configura credenciales SMTP reales |
| `http://127.0.0.1:5000` no conecta | La app no arrancó, o el puerto 5000 está ocupado | Revisa la terminal; cambia `APP_PORT` en `.env` si el puerto está ocupado |
| Tu correo ya está registrado | Los correos deben ser únicos en la tabla `usuarios` | Con Gmail, regístrate con `tunombre+prueba@gmail.com` |
