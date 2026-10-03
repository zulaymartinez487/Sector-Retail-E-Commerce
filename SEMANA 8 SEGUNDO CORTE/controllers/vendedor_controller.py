import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort, g, current_app
from models.producto_model import ProductoModel
from models.pedido_model import PedidoModel, ESTADOS_ENVIO
from models.vendedor_model import VendedorModel
from models.categoria_model import CategoriaModel
from utils.notificador import NotificadorFactory
from utils.envios import TRANSPORTADORAS, crear_envio, crear_transportadora
from utils.logger import Logger

# CONTROLADOR (C de MVC)
# Lado del vendedor: abrir tienda, catálogo/inventario y gestión de envíos.

vendedor_bp = Blueprint("vendedor", __name__, url_prefix="/vendedor")
producto_model = ProductoModel()
pedido_model = PedidoModel()
vendedor_model = VendedorModel()
categoria_model = CategoriaModel()
logger = Logger()

# Firmas de los primeros bytes de cada formato: así no basta con renombrar
# cualquier archivo a ".jpg" para subirlo.
FIRMAS_IMAGEN = {"jpg": (b"\xff\xd8\xff",), "png": (b"\x89PNG",), "webp": (b"RIFF",)}


def _opciones_transportadoras():
    """Transportadoras disponibles (implementaciones del Bridge) con su tarifa y tiempo."""
    return [crear_transportadora(nombre) for nombre in TRANSPORTADORAS]


@vendedor_bp.before_request
def exigir_vendedor():
    if "usuario_id" not in session:
        flash("Inicia sesión para continuar.", "error")
        return redirect(url_for("auth.login", next=request.path))
    g.tienda = vendedor_model.buscar_por_usuario(session["usuario_id"])
    if g.tienda is None and request.endpoint != "vendedor.registro":
        return redirect(url_for("vendedor.registro"))


# ---------- Abrir tienda ----------

@vendedor_bp.route("/registro", methods=["GET", "POST"])
def registro():
    if g.tienda:
        return redirect(url_for("vendedor.panel"))

    if request.method == "POST":
        nombre = request.form.get("nombre_tienda", "").strip()
        descripcion = request.form.get("descripcion", "").strip()[:255]
        ciudad = request.form.get("ciudad", "").strip()[:80]
        transportadora = request.form.get("transportadora", "")

        if not 3 <= len(nombre) <= 100:
            flash("El nombre de la tienda debe tener entre 3 y 100 caracteres.", "error")
        elif vendedor_model.nombre_en_uso(nombre):
            flash("Ya existe una tienda con ese nombre.", "error")
        elif not ciudad:
            flash("Indica la ciudad desde donde despachas.", "error")
        elif transportadora not in TRANSPORTADORAS:
            flash("Elige la transportadora con la que despachas.", "error")
        else:
            vendedor_model.crear(session["usuario_id"], nombre, descripcion, ciudad, transportadora)
            logger.info(f"Nueva tienda '{nombre}' del usuario {session['usuario_id']}.")
            flash(f"¡Tu tienda {nombre} está abierta! Publica tu primer producto.", "success")
            return redirect(url_for("vendedor.nuevo_producto"))

    return render_template("vendedor/registro.html", form=request.form, transportadoras=_opciones_transportadoras())


# ---------- Panel ----------

@vendedor_bp.route("/")
def panel():
    envios = pedido_model.listar_envios_vendedor(g.tienda["id"])
    return render_template(
        "vendedor/panel.html",
        estadisticas=vendedor_model.estadisticas(g.tienda["id"]),
        pendientes=[e for e in envios if e["estado"] in ("pendiente", "preparando")][:5],
        stock_bajo=[p for p in producto_model.listar_por_vendedor(g.tienda["id"]) if p["activo"] and p["stock"] <= 5],
        transportadoras=_opciones_transportadoras(),
    )


@vendedor_bp.route("/transportadora", methods=["POST"])
def cambiar_transportadora():
    transportadora = request.form.get("transportadora", "")
    if transportadora not in TRANSPORTADORAS:
        flash("Transportadora no válida.", "error")
    else:
        # BRIDGE: cambiar la implementación no obliga a tocar las modalidades de envío.
        vendedor_model.cambiar_transportadora(g.tienda["id"], transportadora)
        flash(f"Desde ahora tus envíos se despachan con {transportadora}.", "success")
    return redirect(url_for("vendedor.panel"))


# ---------- Catálogo e inventario ----------

@vendedor_bp.route("/productos")
def productos():
    mis_productos = producto_model.listar_por_vendedor(g.tienda["id"])
    # COMPOSITE: el mismo árbol del catálogo, pero solo con los productos de esta tienda.
    # Cada rama responde cuántos productos, unidades y valor de inventario tiene.
    arbol = categoria_model.construir_arbol(mis_productos)
    return render_template("vendedor/productos.html", productos=mis_productos, arbol=arbol)


def _categorias_para_formulario():
    """Categorías hoja agrupadas por su categoría raíz (para el <select> con <optgroup>)."""
    arbol = categoria_model.construir_arbol()
    grupos = []
    for raiz in arbol.subcategorias():
        hojas = raiz.categorias_hoja()
        grupos.append((raiz.nombre if raiz.subcategorias() else "Otras", hojas))
    # Las raíces sin subcategorías (Deportes, Libros...) se juntan en un solo grupo "Otras".
    otras = [h for nombre, hojas in grupos if nombre == "Otras" for h in hojas]
    return [(n, h) for n, h in grupos if n != "Otras"] + ([("Otras", otras)] if otras else [])


def _guardar_imagen(archivo):
    """Guarda la imagen subida en static/img/productos/ y devuelve su ruta relativa a static/."""
    extension = archivo.filename.rsplit(".", 1)[-1].lower() if "." in archivo.filename else ""
    extension = "jpg" if extension == "jpeg" else extension
    if extension not in FIRMAS_IMAGEN:
        raise ValueError("La imagen debe ser JPG, PNG o WEBP.")
    cabecera = archivo.stream.read(12)
    archivo.stream.seek(0)
    if not cabecera.startswith(FIRMAS_IMAGEN[extension]):
        raise ValueError("El archivo no es una imagen válida.")

    nombre = f"{uuid.uuid4().hex}.{extension}"
    archivo.save(os.path.join(current_app.static_folder, "img", "productos", nombre))
    return f"img/productos/{nombre}"


def _leer_formulario_producto():
    """Valida el formulario de producto. Devuelve (datos, error)."""
    datos = {
        "nombre": request.form.get("nombre", "").strip(),
        "descripcion": request.form.get("descripcion", "").strip()[:2000],
        "categoria_id": request.form.get("categoria_id", type=int),
        "precio": request.form.get("precio", type=int),
        "stock": request.form.get("stock", type=int),
    }
    if not 3 <= len(datos["nombre"]) <= 150:
        return datos, "El nombre debe tener entre 3 y 150 caracteres."
    if not datos["categoria_id"] or not categoria_model.es_hoja(datos["categoria_id"]):
        return datos, "Elige una subcategoría."
    if datos["precio"] is None or not 1000 <= datos["precio"] <= 99_999_999:
        return datos, "El precio debe ser un valor en pesos entre $1.000 y $99.999.999."
    if datos["stock"] is None or not 0 <= datos["stock"] <= 100_000:
        return datos, "El stock debe ser un número entre 0 y 100.000."
    return datos, None


@vendedor_bp.route("/productos/nuevo", methods=["GET", "POST"])
def nuevo_producto():
    if request.method == "POST":
        datos, error = _leer_formulario_producto()
        archivo = request.files.get("imagen")
        if not error and (not archivo or not archivo.filename):
            error = "Sube una foto del producto."
        if not error:
            try:
                datos["imagen"] = _guardar_imagen(archivo)
            except ValueError as e:
                error = str(e)
        if error:
            flash(error, "error")
            return render_template("vendedor/producto_form.html", producto=datos, categorias=_categorias_para_formulario(), nuevo=True)

        producto_model.crear(g.tienda["id"], **datos)
        logger.info(f"Producto '{datos['nombre']}' publicado por la tienda {g.tienda['id']}.")
        flash(f"{datos['nombre']} ya está publicado en el marketplace.", "success")
        return redirect(url_for("vendedor.productos"))

    return render_template("vendedor/producto_form.html", producto={}, categorias=_categorias_para_formulario(), nuevo=True)


@vendedor_bp.route("/productos/<int:producto_id>/editar", methods=["GET", "POST"])
def editar_producto(producto_id):
    producto = producto_model.buscar_por_id(producto_id, incluir_inactivos=True)
    if producto is None or producto["vendedor_id"] != g.tienda["id"]:
        abort(404)

    if request.method == "POST":
        datos, error = _leer_formulario_producto()
        datos["imagen"] = producto["imagen"]
        archivo = request.files.get("imagen")
        if not error and archivo and archivo.filename:
            try:
                datos["imagen"] = _guardar_imagen(archivo)
            except ValueError as e:
                error = str(e)
        if error:
            flash(error, "error")
            return render_template("vendedor/producto_form.html", producto={**producto, **datos},
                                   categorias=_categorias_para_formulario(), nuevo=False)

        producto_model.actualizar(producto_id, g.tienda["id"], **datos)
        flash("Producto actualizado.", "success")
        return redirect(url_for("vendedor.productos"))

    return render_template("vendedor/producto_form.html", producto=producto, categorias=_categorias_para_formulario(), nuevo=False)


@vendedor_bp.route("/productos/<int:producto_id>/activo", methods=["POST"])
def cambiar_activo(producto_id):
    activo = request.form.get("activo") == "1"
    producto_model.cambiar_activo(producto_id, g.tienda["id"], activo)
    flash("Producto publicado de nuevo." if activo else "Producto pausado: ya no aparece en el catálogo.", "success")
    return redirect(url_for("vendedor.productos"))


# ---------- Pedidos y envíos ----------

@vendedor_bp.route("/envios")
def envios():
    estado = request.args.get("estado")
    estado = estado if estado in ESTADOS_ENVIO else None
    return render_template(
        "vendedor/envios.html",
        envios=pedido_model.listar_envios_vendedor(g.tienda["id"], estado),
        estado_actual=estado,
        estados=ESTADOS_ENVIO,
    )


@vendedor_bp.route("/envios/<int:envio_id>", methods=["POST"])
def actualizar_envio(envio_id):
    envio = pedido_model.buscar_envio(envio_id, g.tienda["id"])
    if envio is None:
        abort(404)

    estado = request.form.get("estado")
    transportadora = envio["transportadora"] or g.tienda["transportadora"]
    guia = request.form.get("numero_guia", "").strip()[:60] or envio["numero_guia"]

    if estado not in ESTADOS_ENVIO:
        flash("Estado de envío no válido.", "error")
    elif ESTADOS_ENVIO.index(estado) < ESTADOS_ENVIO.index(envio["estado"]):
        flash("Un envío no puede volver a un estado anterior.", "error")
    else:
        if estado in ("enviado", "entregado") and not guia:
            # BRIDGE: la modalidad del envío delega en su transportadora el formato de la guía.
            guia = crear_envio(envio["modalidad"], transportadora).generar_guia()
        pedido_model.actualizar_envio(envio_id, g.tienda["id"], estado, transportadora, guia)
        if estado != envio["estado"]:
            NotificadorFactory.crear_notificador().enviar_actualizacion_envio(
                envio["correo_comprador"], envio["comprador"], envio["pedido_id"],
                envio["nombre_tienda"], estado, transportadora, guia,
            )
            logger.info(f"Envío {envio_id} (pedido #{envio['pedido_id']}) -> {estado}.")
        flash(f"Envío del pedido #{envio['pedido_id']} actualizado: {estado}.", "success")

    volver = request.form.get("volver", "")
    return redirect(volver if volver.startswith("/vendedor") else url_for("vendedor.envios"))
