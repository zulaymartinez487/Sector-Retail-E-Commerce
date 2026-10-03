from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from models.producto_model import ProductoModel
from models.pedido_model import PedidoModel, StockInsuficienteError, PagoRechazadoError
from models.carrito_model import Carrito
from models.usuario_model import UsuarioModel
from models.vendedor_model import VendedorModel
from models.categoria_model import CategoriaModel
from utils.notificador import NotificadorFactory
from utils.pasarelas_pago import PasarelaPagoFactory, AdaptadorPSE
from utils.cargos_pedido import calcular_costo, CuponDescuento, EmpaqueRegalo
from utils.envios import MODALIDADES
from utils.monedas import MONEDAS, convertir, moneda_valida
from utils.logger import Logger

# CONTROLADOR (C de MVC)
# Lado del comprador: catálogo, tiendas, carrito, pago y pedidos.

tienda_bp = Blueprint("tienda", __name__)
producto_model = ProductoModel()
pedido_model = PedidoModel()
usuario_model = UsuarioModel()
vendedor_model = VendedorModel()
categoria_model = CategoriaModel()
logger = Logger()


@tienda_bp.app_context_processor
def inyectar_datos_comunes():
    # Disponible en todas las vistas: contador del carrito, moneda y tienda del usuario.
    datos = {
        "cantidad_carrito": Carrito(session).cantidad_total(),
        "moneda_actual": moneda_valida(session.get("moneda")),
        "monedas": MONEDAS,
        "mi_tienda": None,
    }
    if "usuario_id" in session:
        datos["mi_tienda"] = vendedor_model.buscar_por_usuario(session["usuario_id"])
    return datos


@tienda_bp.before_request
def exigir_login():
    """Toda la tienda requiere haber iniciado sesión: si no, se va al login."""
    if "usuario_id" not in session:
        # Tras iniciar sesión, vuelve a la página que pidió (si era un GET).
        destino = request.full_path.rstrip("?") if request.method == "GET" else url_for("tienda.inicio")
        if destino == "/":
            return redirect(url_for("auth.login"))
        flash("Inicia sesión para continuar.", "error")
        return redirect(url_for("auth.login", next=destino))


def _volver(por_defecto="tienda.inicio"):
    """Regresa a la página desde donde se envió el formulario."""
    destino = request.form.get("volver", "")
    if destino.startswith("/") and not destino.startswith("//"):
        return redirect(destino)
    return redirect(url_for(por_defecto))


# ---------- Catálogo ----------

@tienda_bp.route("/")
def inicio():
    categoria = request.args.get("categoria", "").strip()
    busqueda = request.args.get("q", "").strip()
    orden = request.args.get("orden", "relevancia")

    # COMPOSITE: el árbol del catálogo con cada producto activo colgado de su categoría.
    arbol = categoria_model.construir_arbol(producto_model.listar())
    nodo = arbol.buscar(categoria) if categoria else None
    if categoria and nodo is None:
        abort(404)

    return render_template(
        "tienda/inicio.html",
        # Filtrar por "Tecnología" incluye todas sus subcategorías: ids de toda la rama.
        productos=producto_model.listar(nodo.ids_categorias() if nodo else None, busqueda or None, orden=orden),
        arbol=arbol,
        nodo=nodo,
        categoria_actual=categoria,
        busqueda=busqueda,
        orden=orden,
    )


@tienda_bp.route("/producto/<int:producto_id>")
def producto(producto_id):
    producto = producto_model.buscar_por_id(producto_id)
    if producto is None:
        abort(404)
    nodo = categoria_model.construir_arbol().buscar(producto["categoria"])
    return render_template(
        "tienda/producto.html",
        producto=producto,
        ruta_categorias=(nodo.ruta() + [nodo]) if nodo else [],
        relacionados=producto_model.listar_relacionados(producto),
        en_carrito=Carrito(session).cantidad_de(producto_id),
    )


@tienda_bp.route("/tienda/<int:vendedor_id>")
def tienda_vendedor(vendedor_id):
    vendedor = vendedor_model.buscar_por_id(vendedor_id)
    if vendedor is None:
        abort(404)
    return render_template(
        "tienda/vendedor_publico.html",
        vendedor=vendedor,
        productos=producto_model.listar(vendedor_id=vendedor_id),
    )


@tienda_bp.route("/moneda", methods=["POST"])
def cambiar_moneda():
    session["moneda"] = moneda_valida(request.form.get("moneda"))
    return _volver()


# ---------- Carrito ----------

@tienda_bp.route("/carrito")
def carrito():
    return render_template(
        "tienda/carrito.html",
        resumen=Carrito(session).resumen(producto_model),
        envio_gratis_desde=Carrito.ENVIO_GRATIS_DESDE,
    )


@tienda_bp.route("/carrito/agregar/<int:producto_id>", methods=["POST"])
def agregar_al_carrito(producto_id):
    producto = producto_model.buscar_por_id(producto_id)
    if producto is None:
        abort(404)

    mi_tienda = vendedor_model.buscar_por_usuario(session["usuario_id"])
    if mi_tienda and mi_tienda["id"] == producto["vendedor_id"]:
        flash("No puedes comprar productos de tu propia tienda.", "error")
        return _volver()

    cantidad = max(request.form.get("cantidad", 1, type=int) or 1, 1)
    carrito = Carrito(session)
    disponible = producto["stock"] - carrito.cantidad_de(producto_id)

    if disponible <= 0:
        flash(f"No quedan más unidades de {producto['nombre']}.", "error")
    else:
        cantidad = min(cantidad, disponible)
        carrito.agregar(producto_id, cantidad)
        flash(f"{producto['nombre']} se agregó al carrito.", "success")
    return _volver()


@tienda_bp.route("/carrito/actualizar/<int:producto_id>", methods=["POST"])
def actualizar_carrito(producto_id):
    producto = producto_model.buscar_por_id(producto_id)
    cantidad = request.form.get("cantidad", 0, type=int) or 0
    if producto is not None and cantidad > producto["stock"]:
        cantidad = producto["stock"]
        flash(f"Solo hay {cantidad} unidades de {producto['nombre']}.", "error")
    Carrito(session).actualizar(producto_id, cantidad)
    return redirect(url_for("tienda.carrito"))


@tienda_bp.route("/carrito/quitar/<int:producto_id>", methods=["POST"])
def quitar_del_carrito(producto_id):
    Carrito(session).quitar(producto_id)
    return redirect(url_for("tienda.carrito"))


# ---------- Pago ----------

def _opciones_checkout():
    """
    Opciones elegidas en el checkout (llegan por GET al actualizar el
    resumen, y como campos ocultos en el POST de pago).
    """
    cupon = request.values.get("cupon", "").strip().upper()
    modalidad = request.values.get("modalidad")
    return {
        "modalidad": modalidad if modalidad in MODALIDADES else "estandar",
        "regalo": request.values.get("regalo") == "1",
        "seguro": request.values.get("seguro") == "1",
        "cupon": cupon,
        "cupon_valido": CuponDescuento.es_valido(cupon),
    }


def _costo(resumen, opciones):
    # DECORATOR: se apilan solo las capas (extras) que eligió el comprador.
    return calcular_costo(resumen["subtotal"], resumen["envio"], opciones["regalo"], opciones["seguro"],
                          opciones["cupon"] if opciones["cupon_valido"] else None)


def _render_checkout(carrito, opciones, formulario=None):
    moneda = moneda_valida(session.get("moneda"))
    resumen = carrito.resumen(producto_model, opciones["modalidad"])
    costo = _costo(resumen, opciones)
    # BRIDGE: costo de envío de cada modalidad con las transportadoras de las tiendas del carrito.
    modalidades = [
        {"codigo": codigo, "nombre": clase.nombre, "envio": carrito.resumen(producto_model, codigo)["envio"]}
        for codigo, clase in MODALIDADES.items()
    ]
    return render_template(
        "tienda/checkout.html",
        resumen=resumen,
        costo=costo,
        opciones=opciones,
        modalidades=modalidades,
        precio_regalo=EmpaqueRegalo.PRECIO,
        cupones=CuponDescuento.CUPONES,
        pasarelas=PasarelaPagoFactory.todas(),
        bancos=AdaptadorPSE().bancos,
        total_moneda=convertir(costo.total(), moneda),
        form=formulario or {},
    )


@tienda_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    carrito = Carrito(session)
    if not carrito.cantidad_total():
        flash("Tu carrito está vacío.", "error")
        return redirect(url_for("tienda.carrito"))

    opciones = _opciones_checkout()
    if opciones["cupon"] and not opciones["cupon_valido"]:
        flash(f"El cupón {opciones['cupon']} no existe.", "error")

    if request.method == "GET":
        return _render_checkout(carrito, opciones)

    # Solo se devuelven al formulario los datos de entrega, nunca los de la tarjeta.
    formulario = {c: request.form.get(c, "").strip() for c in ("direccion", "ciudad", "telefono", "pasarela")}
    if len(formulario["direccion"]) < 5 or len(formulario["ciudad"]) < 3:
        flash("Escribe la dirección y la ciudad de entrega.", "error")
        return _render_checkout(carrito, opciones, formulario)
    if not formulario["telefono"].replace(" ", "").isdigit() or len(formulario["telefono"].replace(" ", "")) < 7:
        flash("Escribe un teléfono de contacto válido.", "error")
        return _render_checkout(carrito, opciones, formulario)

    moneda = moneda_valida(session.get("moneda"))
    try:
        pasarela = PasarelaPagoFactory.crear(formulario["pasarela"])
    except ValueError:
        flash("Elige un medio de pago.", "error")
        return _render_checkout(carrito, opciones, formulario)

    resumen = carrito.resumen(producto_model, opciones["modalidad"])
    if not resumen["grupos"]:
        flash("Los productos de tu carrito ya no están disponibles.", "error")
        return redirect(url_for("tienda.carrito"))
    costo = _costo(resumen, opciones)

    entrega = {
        "direccion": formulario["direccion"],
        "ciudad": formulario["ciudad"],
        "telefono": formulario["telefono"],
        "moneda": moneda,
        "total_moneda": convertir(costo.total(), moneda),
        "pasarela": pasarela.codigo,
    }

    def cobrar(total_cop):
        # ADAPTER: el checkout usa la misma interfaz para cualquier pasarela.
        return pasarela.procesar(convertir(total_cop, moneda), moneda, request.form)

    try:
        pedido_id, referencia = pedido_model.crear_pedido(session["usuario_id"], resumen, costo, entrega, cobrar)
    except StockInsuficienteError as error:
        flash(f"Ya no hay unidades suficientes de {error.nombre_producto}. Ajusta tu carrito.", "error")
        return redirect(url_for("tienda.carrito"))
    except PagoRechazadoError as error:
        logger.warning(f"Pago rechazado ({pasarela.codigo}) para el usuario {session['usuario_id']}: {error}")
        flash(f"Pago rechazado: {error}", "error")
        return _render_checkout(carrito, opciones, formulario)

    carrito.vaciar()
    logger.info(f"Pedido #{pedido_id} pagado con {pasarela.codigo} ({referencia}) por {costo.total()} COP en {moneda}.")

    notificador = NotificadorFactory.crear_notificador()
    comprador = usuario_model.buscar_por_id(session["usuario_id"])
    items = [i for g in resumen["grupos"] for i in g["items"]]
    notificador.enviar_confirmacion_pedido(comprador["correo"], comprador["nombre"], pedido_id, items, costo.total(), moneda)
    for grupo in resumen["grupos"]:
        vendedor = vendedor_model.buscar_por_id(grupo["vendedor_id"])
        dueno = usuario_model.buscar_por_id(vendedor["usuario_id"])
        notificador.enviar_nueva_venta(dueno["correo"], grupo["nombre_tienda"], pedido_id, grupo["items"], grupo["subtotal"])

    flash(f"¡Pago aprobado! Tu pedido #{pedido_id} fue confirmado (referencia {referencia}).", "success")
    return redirect(url_for("tienda.mis_pedidos"))


@tienda_bp.route("/mis-pedidos")
def mis_pedidos():
    return render_template(
        "tienda/mis_pedidos.html",
        pedidos=pedido_model.listar_por_usuario(session["usuario_id"]),
    )
